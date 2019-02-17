#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import math
from uuid import uuid4
from array import array
from collections import defaultdict

from Pad import Pad
from Plot import Plot
from MethodProxy import *
from Canvas import Canvas
from IOManager import IOManager
from Helpers import DissectProperties, MergeDicts


@PreloadProperties
class Histo1D(MethodProxy, ROOT.TH1D):

    ROOT.TH1.SetDefaultSumw2(True)

    def __init__(self, name="undefined", *args, **kwargs):
        MethodProxy.__init__(self)
        self._varexp = None
        self._cuts = None
        self._weight = None
        self._drawoption = ""
        self._drawerrorband = False
        if len(args) == 1:
            if isinstance(args[0], list):
                lowbinedges = array("d", args[0])
                ROOT.TH1D.__init__(self, name, "", len(lowbinedges) - 1, lowbinedges)
            elif isinstance(args[0], ROOT.TH1D) or isinstance(args[0], Histo1D):
                ROOT.TH1D.__init__(self, args[0].Clone(name))
                self.SetDirectory(0)
        elif len(args) == 3 and isinstance(args[0], int):
            ROOT.TH1D.__init__(self, name, "", *args)
        else:
            raise TypeError
        if not name.endswith("_errorband"):
            self._errorband = Histo1D("{}_errorband".format(self.GetName()), self)
            self.__class__._properties += [
                "errorband{}".format(p) for p in self.__class__._properties
            ]  # *append* properties of members!
        self.DeclareProperties(**kwargs)
        self._lowbinedges = IOManager._getBinning(self)["xbinning"]
        self._nbins = len(self._lowbinedges) - 1
        self._attalpha = defaultdict(lambda: 1.0)

    def DeclareProperty(self, property, args):
        # Properties starting with "errorband" will be applied to self._errorband.
        # All errorband properties will be applied after the main histo properties.
        # By default the errorband fillcolor and markercolor matches the histograms
        # linecolor.
        property = property.lower()
        if property.startswith("errorband"):
            super(Histo1D, self._errorband).DeclareProperty(property[9:], args)
        else:
            super(Histo1D, self).DeclareProperty(property, args)
            if property == "linecolor":
                errbndcol = args
            elif property == "linecoloralpha":
                errbndcol = args[0]
            else:
                return
            super(Histo1D, self._errorband).DeclareProperty("fillcolor", errbndcol)
            super(Histo1D, self._errorband).DeclareProperty("markercolor", errbndcol)

    def Fill(self, *args, **kwargs):
        self._varexp = kwargs.get("varexp")
        self._cuts = kwargs.get("cuts", [])
        self._weight = kwargs.get("weight", "1")
        if len(args) == 1 and isinstance(args[0], str):
            IOManager.FillHistogram(self, args[0], **kwargs)
            if not kwargs.get("append", False):
                self._errorband.Reset()
            self._errorband.Add(self)
        else:
            super(Histo1D, self).Fill(*args)

    def SetDrawOption(self, string):
        if not isinstance(string, str) and not isinstance(string, unicode):
            raise Type
        self._drawoption = string
        super(Histo1D, self).SetDrawOption(string)

    def GetDrawOption(self):
        return self._drawoption

    def SetDrawErrorband(self, boolean):
        self._drawerrorband = boolean

    def GetDrawErrorband(self):
        return self._drawerrorband

    def GetXTitle(self):
        return self.GetXaxis().GetTitle()

    def GetYTitle(self):
        return self.GetYaxis().GetTitle()

    def Draw(self, drawoption=None):
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        self.DrawCopy(self.GetDrawOption(), "_{}".format(uuid4().hex[:8]))
        if self._drawerrorband:
            self._errorband.DrawCopy(
                self._errorband.GetDrawOption() + "SAME", "_{}".format(uuid4().hex[:8])
            )

    def GetBinWidths(self):
        binwidths = [
            self._lowbinedges[i + 1] - self._lowbinedges[i]
            for i in range(len(self._lowbinedges) - 1)
        ]
        return binwidths

    def BuildFrame(self, **kwargs):
        scale = 1.0 + kwargs.get(
            "ypadding", 0.2
        )  # default: frame is 20% higher than maximum
        logx = kwargs.get("logx", False)
        logy = kwargs.get("logy", False)
        xtitle = kwargs.get("xtitle", None)
        ytitle = kwargs.get("ytitle", "Entries")
        xunits = kwargs.get("xunits", None)
        if xtitle is None:
            xtitle = self._varexp if self._varexp is not None else ""
        binwidths = self.GetBinWidths()
        if len(set(binwidths)) == 1:
            binwidth = binwidths[0]
            ytitle += " / {}".format(
                int(binwidth) if binwidth.is_integer() else round(binwidth, 1)
            )
            if xunits:
                ytitle += " {}".format(xunits)
        frame = {
            "xmin": self._lowbinedges[0],
            "xmax": self._lowbinedges[self._nbins],
            "ymin": 0.0,
            "ymax": self.GetMaximum(),
            "xtitle": xtitle,
            "ytitle": ytitle,
        }
        if logx:
            frame["xmin"] = 1e-2
        if logy:
            frame["ymin"] = 1e-2
            frame["ymax"] = 10 ** (
                scale
                * math.log10(
                    10 ** (math.log10(frame["ymax"]) - math.log10(frame["ymin"]))
                )
                + math.log10(frame["ymin"])
            )
        else:
            frame["ymax"] *= scale
        return frame

    def Print(self, path, **kwargs):
        units = kwargs.pop("units", None)
        properties = DissectProperties(kwargs, [Histo1D, Plot, Canvas, Pad])
        xtitle, ytitle = self.GetXTitle(), self.GetYTitle()
        if units:
            xtitle += " [{}]".format(str(units))
            ytitle += " {}".format(str(units))
        properties["Histo1D"].setdefault("xtitle", xtitle)
        properties["Histo1D"].setdefault("ytitle", ytitle)
        plot = Plot()
        plot.Register(self, **MergeDicts(properties["Histo1D"], properties["Pad"]))
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def Add(self, histo, scale=1):
        raw_entries = self.GetEntries() + histo.GetEntries()
        super(Histo1D, self).Add(histo, scale)
        self.SetEntries(raw_entries)

    def SetBinLabel(self, index, label, **kwargs):
        scale = kwargs.pop("scale", 1.0)
        option = kwargs.pop("option", "h")
        if kwargs:
            raise KeyError(
                "Unknown keyword argument(s) '{}'".format(", ".join(kwargs.keys()))
            )
        xaxis = self.GetXaxis()
        xaxis.SetLabelSize(xaxis.GetLabelSize() * scale)
        xaxis.SetBinLabel(index, label)
        self.LabelsOption(option)

    def SetLineAlpha(self, alpha):
        self._attalpha["line"] = alpha
        self.SetLineColorAlpha(self.GetLineColor(), alpha)

    def SetFillAlpha(self, alpha):
        self._attalpha["fill"] = alpha
        self.SetFillColorAlpha(self.GetFillColor(), alpha)

    def SetMarkerAlpha(self, alpha):
        self._attalpha["marker"] = alpha
        self.SetMarkerColorAlpha(self.GetMarkerColor(), alpha)

    def SetLineColor(self, color):
        self.SetLineColorAlpha(color, self._attalpha["line"])

    def SetFillColor(self, color):
        self.SetFillColorAlpha(color, self._attalpha["fill"])

    def SetMarkerColor(self, color):
        self.SetMarkerColorAlpha(color, self._attalpha["marker"])

    def SetErrorX(self, value=0.5):
        ROOT.gStyle.SetErrorX(value)


def main():

    filename = "../data/ds_data18.root"
    h = Histo1D("test", 20, 0.0, 400.0)
    Histo1D.PrintAvailableProperties()
    h.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    print(h)
    print(h.Integral())
    h.Print(
        "test_histo_data.pdf", template="data", units="GeV", logy=False, xunits="GeV"
    )
    h.Print(
        "test_histo_background.pdf",
        template="background",
        units="GeV",
        logy=False,
        xunits="GeV",
    )
    h.Print(
        "test_histo_signal.pdf",
        template="signal",
        units="GeV",
        linecolor=ROOT.kViolet,
        drawerrorband=True,
        logy=True,
        xunits="GeV",
    )


if __name__ == "__main__":
    main()
