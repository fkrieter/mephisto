#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import os

from Stack import Stack
from MethodProxy import *
from Histo1D import Histo1D
from CutMarker import CutMarker
from IOManager import IOManager
from SensitivityScan import SensitivityScan
from Helpers import DissectProperties, MergeDicts, SplitCutExpr, clean_str

from uuid import uuid4


@PreloadProperties
class N1Plotter(MethodProxy):
    r"""Class for N-1 plots.
    """

    def __init__(self, name=uuid4().hex[:8], **kwargs):
        self._name = name
        self._cuts = []  # list of all common cuts
        self._drawcuts = []  # tuples of varexps and associated cut values to be drawn
        self._binning = {}
        self._configs = {"background": [], "signal": []}
        self._store = {}
        self._preselection = []
        self._formatfields = ["varexp", "comparator", "cutvalue"]
        self._outputformat = "N-1_{varexp}_{cutvalue}.pdf"
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)

    def SetCuts(self, *cuts):
        tmpcutlist = []
        if isinstance(cuts, str):
            cuts = cuts.split("&&")
        elif not isinstance(cuts, (list, tuple)):
            raise TypeError
        for cutexpr in cuts:
            tmpcutlist += cutexpr.split("&&")
        self._cuts = []
        self._drawcuts = []
        for cutexpr in tmpcutlist:
            if not "||" in cutexpr:
                cutexpr = clean_str(cutexpr, remove="()")
                splt = SplitCutExpr(cutexpr)
                self._drawcuts.append(
                    (splt["varexp"], splt["comparator"], splt["value"])
                )
            self._cuts.append(cutexpr)

    def GetCuts(self):
        return self._cuts

    def SetPreselection(self, *cuts):
        if not isinstance(cuts, (str, list, tuple)):
            raise TypeError
        self._preselection = list(cuts)

    def GetPreselection(self):
        return self._preselection

    def SetBinning(self, varexp, *args):
        if len(args) == 3:
            self._binning[varexp] = IOManager._convertBinning(args)
        elif len(args) == 1 and isinstance(args[0], list):
            self._binning[varexp] = args[0]
        else:
            logger.error(
                "Invalid binning format '{}' for varexp '{}'!".format(args, varexp)
            )

    def GetBinning(self, varexp):
        return self._binning[varexp]

    def SetBinnings(self, binningdict):
        for varexp, binning in binningdict.items():
            self.SetBinning(varexp, *binning)

    def GetBinnings(self):
        return self._binning

    def Register(self, infile, **kwargs):
        histotype = kwargs.pop("type")
        assert histotype.lower() in self._configs.keys()
        assert "tree" in kwargs
        assert "varexp" not in kwargs
        template = kwargs.pop("template", {})
        self._configs[histotype.lower()].append(
            (infile, MergeDicts(Histo1D.GetTemplate(template), kwargs))
        )

    def CreateHistograms(self):
        factories = {}
        for histotype, configs in self._configs.items():
            self._store[histotype] = {}
            for i, (infile, config) in enumerate(configs):
                self._store[histotype][i] = {}
                config = DissectProperties(
                    config, [Histo1D, {"Fill": ["tree", "cuts", "weight"]}]
                )
                tree = config["Fill"]["tree"]
                if not (infile, tree) in factories.keys():
                    factories[infile, tree] = IOManager.Factory(infile, tree)
                for varexp, comparator, cutvalue in self._drawcuts:
                    if not varexp in self._binning:
                        logger.warning(
                            "No binning defined for varexp '{}'. "
                            "Skipping...".format(varexp)
                        )
                        continue
                    reducedcuts = list(
                        filter(
                            lambda x: x != "".join([varexp, comparator, cutvalue]),
                            self._cuts,
                        )
                    )
                    self._store[histotype][i][varexp, cutvalue] = Histo1D(
                        "N1_{}".format(uuid4().hex[:8]),
                        "",
                        self._binning[varexp],
                        **config["Histo1D"]
                    )
                    factories[infile, tree].Register(
                        self._store[histotype][i][varexp, cutvalue],
                        varexp=varexp,
                        weight=config["Fill"].get("weight", "1"),
                        cuts=list(
                            config["Fill"].get("cuts", [])
                            + reducedcuts
                            + self._preselection
                        ),
                    )
        for factory in factories.values():
            factory.Run()

    def SetOutputFormat(self, pattern):
        fields = re.findall(r"{(.*?)}", pattern)
        for field in fields:
            if not field in self._formatfields:
                logger.error(
                    "Invalid field '{}' in output format '{}'!".format(field, pattern)
                )
                raise KeyError
        self._outputformat = pattern

    def GetOutputFormat(self):
        return self._outputformat

    def FormatOutput(self, **kwargs):
        formatdict = {k: "{" + k + "}" for k in self._formatfields}
        for key, value in kwargs.items():
            if not key in self._formatfields:
                logger.error("Output formatting failed: Invalid key '{}'!".format(key))
                raise KeyError
            formatdict[key] = value
        outputfilename = self._outputformat.format(**formatdict)
        return outputfilename

    def Print(self, outputdir, **kwargs):
        # TODO: Use actual signal and background histograms for the SensitivityScan as
        # defined in Register instead of what is 'guessed' by Stack.Print.
        kwargs.setdefault("sensitivity", True)
        self.CreateHistograms()
        for varexp, comparator, cutvalue in self._drawcuts:
            if not varexp in self._binning:
                continue
            stack = Stack()
            for histotype, histos in self._store.items():
                for i, histo in histos.items():
                    stack.Register(histo[varexp, cutvalue])
            direction = "-" if "<" in comparator else "+"
            cutmarkerprops = {
                "direction": direction,
                "drawarrow": any([s in comparator for s in "<>"]),
            }
            if kwargs.get("sensitivity"):
                kwargs.setdefault("direction", direction)
            cutmarker = CutMarker(float(cutvalue), **cutmarkerprops)
            stack.Print(
                os.path.join(
                    outputdir,
                    self.FormatOutput(
                        varexp=varexp, comparator=comparator, cutvalue=cutvalue
                    ),
                ),
                inject0=cutmarker,
                **kwargs
            )


if __name__ == "__main__":

    testsamples = []

    for i in range(4):
        testsamples.append("../data/testsample_{}.root".format(i))
        try:
            IOManager.CreateTestSample(testsamples[i], overwrite=False)
        except IOError:
            pass

    cuts = ["branch_4>1.5", "branch_5<2.5", "branch_6>=4.5"]

    binnings = {
        "branch_4": [20, 0.0, 10.0],  # fixed bin width
        "branch_5": [20, 0.0, 10.0],
        "branch_6": [
            [i * 0.25 for i in range(40)] + [10, 11, 12, 13, 14, 15, 17.5, 20]
        ],  # variable bin width
    }

    n1plotter = N1Plotter(cuts=cuts, binnings=binnings)
    n1plotter.Register(
        testsamples[0],
        type="background",
        tree="tree",
        weight="2.0*branch_5/(branch_4*branch_6)",
        title="Bkg. 1",
        template="background",
        fillcolor="#2e95bb",
    )
    n1plotter.Register(
        testsamples[1],
        type="background",
        tree="tree",
        weight="3.0*branch_5/(branch_4*branch_6)",
        title="Bkg. 2",
        template="background",
        fillcolor="#2ebb7c",
    )
    n1plotter.Register(
        testsamples[2],
        type="background",
        tree="tree",
        weight="4.0*branch_5/(branch_4*branch_6)",
        title="Bkg. 3",
        template="background",
        fillcolor="#9451b4",
    )
    n1plotter.Register(
        testsamples[3],
        type="signal",
        tree="tree",
        weight="5.0/branch_10",
        title="Signal",
        template="signal",
        fillcolor=ROOT.kRed,
    )
    n1plotter.Print("n1plots", mkdir=True)  # output directory
