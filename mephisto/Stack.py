#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from Histo1D import Histo1D
from Helpers import DissectProperties, MephistofyObject, MergeDicts


def ExtendProperties(cls):
    # Add properties to configure the _stacksumhisto member histogram of Stacks.
    cls._properties += ["stacksum{}".format(p) for p in Histo1D._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Stack(MethodProxy, ROOT.THStack):
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
                if args[0]._stacksumhisto is not None:
                    self._stacksumhisto = Histo1D("{}_stacksum", args[0]._stacksumhisto)
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

    def DeclareProperty(self, property, args):
        # Properties starting with "stacksum" will be applied to self._stacksumhisto.
        # All stacksum properties will be applied after the main stack properties.
        property = property.lower()
        if property.startswith("stacksum"):
            self._stacksumhisto.DeclareProperty(property[8:], args)
        else:
            super(Stack, self).DeclareProperty(property, args)

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
        stack = kwargs.pop("stack", False)
        histo.SetDrawErrorband(False)
        if stack:
            if self._stacksumhisto is None:
                self._stacksumhisto = Histo1D(
                    "{}_totalstack".format(self.GetName()), histo
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
        use_ymin = kwargs.pop("use_ymin", False)
        use_ymax = kwargs.pop("use_ymax", False)
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
        ymin = frame["ymin"] if not use_ymin else kwargs.get("ymin")
        ymax = frame["ymax"] if not use_ymax else kwargs.get("ymax")
        Stack.UpdateYAxisRange(self, ymin, ymax, logy)
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
            # TODO: Fix these:
            stack.SetMaximum(ymax / (1 + 0.2 * ROOT.TMath.Log10(ymax / ymin)))
            stack.SetMinimum(ymin * (1 + 0.5 * ROOT.TMath.Log10(ymax / ymin)))

    def Print(self, path, **kwargs):
        from RatioPlot import RatioPlot
        from ContributionPlot import ContributionPlot

        contribution = kwargs.pop("contribution", False)
        ratio = kwargs.pop("ratio", False)
        if ratio is True:
            try:  # it's just a guess...
                datahisto = filter(
                    lambda h: h.GetDrawOption().upper() != "HIST",
                    self._store["nostack"],
                )[0]
                ratio = [datahisto, self._stacksumhisto]
            except IndexError:
                logger.error(
                    "Failed to identify appropriate numerator histogram for RatioPlot "
                    "pad!"
                )
                ratio = False
        npads = sum([contribution, bool(ratio)]) + 1
        properties = DissectProperties(kwargs, [Stack, Plot, Canvas, Pad])
        self.BuildStack()
        plot = Plot(npads=npads)
        plot.Register(self, **MergeDicts(properties["Stack"], properties["Pad"]))
        if self._drawstacksum and self._stacksumhisto is not None:
            addstacksumtolegend = self._stacksumhisto.GetAddToLegend()
            plot.Register(self._stacksumhisto, addtolegend=False)
            if self._stacksumhisto.GetAddToLegend():
                # Dummy histo with the correct legend entry styling:
                h = Histo1D(
                    "{}_legendentry".format(self._stacksumhisto.GetName()),
                    self._stacksumhisto.GetTitle(),
                    [0, 1],
                )
                plot.Register(
                    h,
                    linecolor=self._stacksumhisto.GetLineColor(),
                    fillcolor=self._stacksumhisto._errorband.GetFillColor(),
                    fillstyle=self._stacksumhisto._errorband.GetFillStyle(),
                    legenddrawoption=self._stacksumhisto.GetLegendDrawOption(),
                )
        for histo in self._store["nostack"]:
            plot.Register(histo, **properties["Pad"])
        if contribution:
            contribplot = ContributionPlot(self)
            plot.Register(
                contribplot,
                pad=1,
                ytitle="Contrib.",
                logy=False,
                ymin=0,
                ymax=1,
                xtitle=properties["Pad"]["xtitle"],
                xunits=properties["Pad"]["xunits"],
            )
        if ratio:
            ratioplot = RatioPlot(*ratio)
            plot.Register(
                ratioplot,
                pad=npads - 1,
                ytitle="Data / SM",
                logy=False,
                ymin=0.2,
                ymax=1.8,
                xtitle=properties["Pad"]["xtitle"],
                xunits=properties["Pad"]["xunits"],
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

    s.Print(
        "test_stack.pdf",
        contribution=True,
        ratio=True,
        # ymax=3e2,
        logy=False,
        xtitle="E_{T}^{miss}",
        xunits="GeV",
        luminosity=139,
    )
