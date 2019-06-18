#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4
from distutils.spawn import find_executable

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from Histo1D import Histo1D
from Helpers import CheckPath, DissectProperties, MephistofyObject, MergeDicts, TeX2PDF


def ExtendProperties(cls):
    # Add properties to configure the _stacksumhisto member histogram of Stacks.
    cls._properties += ["stacksum{}".format(p) for p in Histo1D._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Stack(MethodProxy, ROOT.THStack):

    _ignore_properties = ["name", "xtitle", "ytitle", "ztitle", "histogram"]

    def __init__(self, name=uuid4().hex[:8], *args, **kwargs):
        MethodProxy.__init__(self)
        self._stacksumhisto = None
        self._stacksumproperties = {}
        self._stacksorting = None
        self._drawoption = ""
        self._drawstacksum = False
        self._store = dict(stack=[], nostack=[])
        if len(args) == 0:
            ROOT.THStack.__init__(self, name, "")
        elif len(args) == 1:
            if isinstance(args[0], str):
                ROOT.THStack.__init__(self, name, args[0])
            elif args[0].InheritsFrom("THStack"):
                ROOT.THStack.__init__(self, args[0])
                self.SetName(name)
                if args[0].__class__.__name__ == "Stack":
                    if args[0]._stacksumhisto is not None:
                        self._stacksumhisto = Histo1D(
                            "{}_stacksum", args[0]._stacksumhisto
                        )
                    for key, store in args[0]._store.items():
                        for histo in store:
                            self._store[key].append(
                                Histo1D("{}_{}".format(histo.GetName(), name), histo)
                            )
                    self.DeclareProperties(**args[0].GetProperties())
            else:
                raise TypeError
        else:
            raise TypeError
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        properties = DissectProperties(
            kwargs,
            [
                {
                    "Stacksum": [
                        "stacksum{}".format(p) for p in Histo1D.GetListOfProperties()
                    ]
                },
                Stack,
            ],
        )
        self.DeclareProperties(**properties["Stack"])
        self._stacksumproperties = properties["Stacksum"]

    @CheckPath(mode="w")
    def PrintYieldTable(self, path=None, **kwargs):
        silent = kwargs.pop("silent", False)  # don't print table to stdout
        precision = kwargs.pop("precision", 2)
        crop = kwargs.pop("crop", True)  # get a nice PDF table!
        yields = [["Process", "Yield", "Stat. error", "Raw"]]
        for histo in (
            sorted(
                self._store["stack"],
                key=lambda h: h.Integral(0, h.GetNbinsX() + 1),
                reverse=True,
            )
            + [self._stacksumhisto]
            + sorted(
                self._store["nostack"],
                key=lambda h: h.Integral(0, h.GetNbinsX() + 1),
                reverse=True,
            )
        ):
            staterr = ROOT.Double(0)
            integral = "{:.{prec}f}".format(
                histo.IntegralAndError(0, histo.GetNbinsX() + 1, staterr),
                prec=precision,
            )
            staterr = "{:.{prec}f}".format(staterr, prec=precision)
            raw = str(int(histo.GetEntries()))
            yields.append([histo.GetTitle(), integral, staterr, raw])
        colwidths = [
            max(w) for w in zip(*[[len(str(e)) for e in entries] for entries in yields])
        ]
        if not silent:
            for i, row in enumerate(yields):
                for j, item in enumerate(row):
                    print(
                        str(item).ljust(colwidths[j])
                        if j == 0
                        else str(item).rjust(colwidths[j] + 4),
                        end="" if j < len(row) - 1 else "\n",
                    )
                if i == len(self._store["stack"]):
                    print("-" * (sum(colwidths) + (len(colwidths) - 1) * 4))
        if path is not None:
            if path.endswith(".csv"):
                with open(path, "w") as out:
                    for row in yields:
                        out.write(";".join(row) + "\n")
            elif path.endswith((".tex", ".pdf")):
                latextable = []
                latextable.append("""\\begin{tabular}{lrlr}""")
                latextable.append("""\\toprule""")
                for i, row in enumerate(yields):
                    if i == 0:
                        latextable.append(
                            """{} \\\\""".format(
                                " & ".join(["""\\textbf{""" + e + """}""" for e in row])
                            )
                        )
                        latextable.append("""\\midrule""")
                    else:
                        latextable.append(
                            """{} \\\\""".format(
                                " & ".join(
                                    [
                                        r"$\pm$ " + e if j == 2 else e
                                        for j, e in enumerate(row)
                                    ]
                                )
                            )
                        )
                        if i == len(self._store["stack"]):
                            latextable.append("""\midrule""")
                latextable.append("""\\bottomrule""")
                latextable.append("""\\end{tabular}""")
                if path.endswith(".tex"):
                    with open(path, "w") as out:
                        for line in latextable:
                            out.write(line + "\n")
                if path.endswith(".pdf"):
                    if find_executable("pdflatex") is None:
                        logger.error(
                            "Cannot compile LaTeX yields table: Command "
                            "'pdflatex' not found!"
                        )
                    elif crop and find_executable("pdfcrop") is None:
                        logger.error(
                            "Cannot crop PDF yields table: Command 'pdfcrop' not found!"
                        )
                        crop = False
                    else:
                        TeX2PDF("\n".join(latextable), path, crop=crop)  # verbosity=2
            else:
                raise IOError(
                    "File extension '{}' not supported!".format(path.split(".")[-1])
                )
            logger.info("Created yields table: '{}'".format(path))

    def DeclareProperty(self, property, args):
        # Properties starting with "stacksum" will be applied to self._stacksumhisto.
        # All stacksum properties will be applied after the main stack properties.
        property = property.lower()
        if property.startswith("stacksum"):
            self._stacksumhisto.DeclareProperty(property[8:], args)
        else:
            super(Stack, self).DeclareProperty(property, args)

    def GetProperty(self, property):
        if property.startswith("stacksum"):
            return self._stacksumhisto.GetProperty(property[8:])
        else:
            super(Stack, self).GetProperty(property)

    def AddStackSortingProperty(self, property, reverse=False):
        if self._stacksorting is None:
            self._stacksorting = []
        self._stacksorting.append((property, reverse))

    def SetStackSorting(self, *listoftuples):
        for property, reverse in listoftuples:
            self.AddStackSortingProperty(property, reverse)

    def GetStackSorting(self):
        return self._stacksorting

    @MephistofyObject(copy=True)
    def Register(self, histo, **kwargs):
        stack = kwargs.pop("stack", histo.GetStack())
        histo.SetDrawErrorband(False)
        if stack:
            if self._stacksumhisto is None:
                self._stacksumhisto = Histo1D(
                    "{}_totalstack".format(self.GetName()),
                    histo,
                    title=self._stacksumproperties.get("stacksumtitle", None),
                )
            else:
                self._stacksumhisto.Add(histo)
        histo.DeclareProperties(**kwargs)
        self._store["stack" if stack else "nostack"].append(histo)

    def SortStack(self):
        if self._stacksorting is not None:
            for prop, reverse in reversed(self._stacksorting):
                if prop in [m.lower() for m in Histo1D._properties]:
                    self._store["stack"].sort(
                        key=lambda h: h.GetProperty(prop), reverse=reverse
                    )
                else:
                    try:
                        self._store["stack"].sort(
                            key=lambda h: getattr(h, prop.capitalize())(),
                            reverse=reverse,
                        )
                    except AttributeError:
                        logger.error(
                            "Sorting failed: 'Histo1D' has no attribute '{}'!".format(
                                prop.capitalize()
                            )
                        )
                        raise AttributeError

    def BuildStack(self, **kwargs):
        if self.GetNhists() != 0:
            return
        if kwargs.get("sort", True):
            self.SortStack()
        for histo in self._store["stack"]:
            self.Add(histo, histo.GetDrawOption())
        self.DeclareProperties(**self._stacksumproperties)

    def BuildFrame(self, **kwargs):
        logy = kwargs.get("logy", False)
        frame = {}
        for histo in [self._stacksumhisto] + self._store["nostack"]:
            if not frame:
                frame = histo.BuildFrame(**kwargs)
            else:
                for key, func in [
                    ("xmin", min),
                    ("ymin", min),
                    ("xmax", max),
                    ("ymax", max),
                ]:
                    frame[key] = func(frame[key], histo.BuildFrame(**kwargs)[key])
        Stack.UpdateYAxisRange(self, frame["ymin"], frame["ymax"], logy)
        return frame

    @staticmethod
    def UpdateYAxisRange(stack, ymin, ymax, logy=False):
        # The THStack y-range problem is super annoying and unfortunately not fully
        # solved by drawing a pad frame first (for plots with mutliple pads the y-range
        # for the first drawn pad (with a THStack in it) is ignored).
        # So here's a fix for that:
        # (See: https://root-forum.cern.ch/t/trouble-w-stackhistograms/12390)
        if not logy:
            stack.SetMaximum(ymax / (1 + ROOT.gStyle.GetHistTopMargin()))
            stack.SetMinimum(ymin)
        else:
            stack.SetMaximum(ymax / (1 + 0.2 * ROOT.TMath.Log10(ymax / ymin)))
            stack.SetMinimum(ymin * (1 + 0.5 * ROOT.TMath.Log10(ymax / ymin)))

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        from RatioPlot import RatioPlot
        from SensitivityScan import SensitivityScan
        from ContributionPlot import ContributionPlot

        contribution = kwargs.pop("contribution", False)
        ratio = kwargs.pop("ratio", False)
        sensitivity = kwargs.pop("sensitivity", False)
        if ratio is True:
            try:  # it's just a guess...
                datahisto = filter(
                    lambda h: not h.GetDrawOption().upper().startswith("HIST"),
                    self._store["nostack"],
                )[0]
                ratio = [datahisto, self._stacksumhisto]  # overwrite boolean
            except IndexError:
                logger.error(
                    "Failed to identify appropriate numerator histogram for RatioPlot "
                    "pad!"
                )
                ratio = False
        if sensitivity:
            try:  # again just making assumptions here...
                sensitivity = filter(
                    lambda h: "HIST" in h.GetDrawOption().upper(),
                    self._store["nostack"],  # overwrite boolean with list of sig histos
                )
            except IndexError:
                logger.error(
                    "Failed to identify appropriate numerator histogram for RatioPlot "
                    "pad!"
                )
                sensitivity = False
        npads = sum([contribution, bool(ratio), bool(sensitivity)]) + 1
        properties = DissectProperties(kwargs, [Stack, Plot, Canvas, Pad])
        self.BuildStack()
        plot = Plot(npads=npads)
        # Register the Stack to the upper Pad (pad=0):
        plot.Register(self, **MergeDicts(properties["Stack"], properties["Pad"]))
        if self._drawstacksum and self._stacksumhisto.GetAddToLegend():
            # Dummy histo with the correct legend entry styling:
            htmp = Histo1D(
                "{}_legendentry".format(self._stacksumhisto.GetName()),
                self._stacksumhisto.GetTitle(),
                [0, 1],
                **{
                    k[8:]: v
                    for k, v in DissectProperties(
                        properties["Stack"],
                        [
                            {
                                "Stacksum": [
                                    "stacksum{}".format(p)
                                    for p in Histo1D.GetListOfProperties()
                                ]
                            }
                        ],
                    )["Stacksum"].items()
                }
            )
            plot.Register(
                htmp,
                fillcolor=self._stacksumhisto._errorband.GetFillColor(),
                fillstyle=self._stacksumhisto._errorband.GetFillStyle(),
                legenddrawoption=self._stacksumhisto.GetLegendDrawOption(),
                **properties["Pad"]
            )
        idx = 1
        xaxisprops = {
            k: v for k, v in properties["Pad"].items() if k in ["xtitle", "xunits"]
        }
        if contribution:
            contribplot = ContributionPlot(self)
            plot.Register(
                contribplot,
                pad=idx,
                ytitle="Contrib.",
                logy=False,
                ymin=0,
                ymax=1,
                **xaxisprops
            )
            idx += 1
        if ratio:
            ratioplot = RatioPlot(*ratio)
            plot.Register(
                ratioplot,
                pad=idx,
                ytitle="Data / SM",
                logy=False,
                ymin=0.2,
                ymax=1.8,
                **xaxisprops
            )
            idx += 1
        if sensitivity:
            sensitivityscan = SensitivityScan(sensitivity, self._stacksumhisto)
            plot.Register(
                sensitivityscan,
                pad=idx,
                ytitle="Z_{N}-value",  # default (see template 'common')
                logy=False,
                **xaxisprops
            )
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def SetDrawOption(self, option):
        # For some reason a THStack must be drawn with "SAMESAME" in the drawoption...
        # For "LEGO" and "SURF" drawoption "SAME" must not be added and the pad should
        # best be initialized with the "drawframe" property set to False!
        self._drawoption = option
        if not any(opt in self._drawoption.upper() for opt in ["LEGO", "SURF"]):
            self._drawoption += "SAME"
        super(Stack, self).SetDrawOption(option)

    def GetDrawOption(self):
        return self._drawoption

    def SetDrawStackSum(self, boolean):
        self._drawstacksum = boolean

    def GetDrawStackSum(self):
        return self._drawstacksum

    def Draw(self, drawoption=None):
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        super(Stack, self).Draw(self.GetDrawOption())
        for histo in self._store["nostack"]:
            histo.Draw(histo.GetDrawOption() + "SAME")
        if self._drawstacksum:
            self._stacksumhisto.Draw(self._stacksumhisto.GetDrawOption() + "SAME")


if __name__ == "__main__":

    filename = "../data/ds_data18.root"

    nbkgs = 6

    threshold = (
        [220]
        + [450]
        + [500 + i * (200.0 / nbkgs) for i in range(nbkgs - 1)]
        + [420, 470]
    )

    h = {}
    s = Stack()
    nbkgs += 1
    for i in range(1, 1 + nbkgs + 2, 1):
        h[i] = Histo1D("h{}".format(i), "Histogram {}".format(i), 20, 0.0, 400.0)
        h[i].Fill(
            filename,
            tree="DirectStau",
            varexp="MET",
            cuts="tau1Pt>{}".format(threshold[i - 1]),
        )
        if i > 1 and i <= nbkgs:
            s.Register(h[i], stack=True, template="background", fillcolor=i)
    s.Register(h[1], stack=False, template="data")
    s.Register(h[nbkgs + 1], stack=False, template="signal", linecolor="#ff8200")
    s.Register(h[nbkgs + 2], stack=False, template="signal", linecolor="#00c892")

    s.PrintYieldTable("tmp/table.pdf", mkdir=True)

    for j in range(4):
        s.Print(
            "test_stack_{}.pdf".format(j),
            contribution=j >= 1,
            ratio=j >= 2,
            sensitivity=j >= 3,
            # ymax=1e5,
            ymin=1e-1,
            logy=True,
            xtitle="E_{T}^{miss}",
            xunits="GeV",
            luminosity=139,
            stacksumtitle="SUM",
        )
