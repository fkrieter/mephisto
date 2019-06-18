#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4
from array import array
from collections import defaultdict

from Pad import Pad
from Plot import Plot
from MethodProxy import *
from Canvas import Canvas
from IOManager import IOManager
from Helpers import DissectProperties, MergeDicts, CheckPath, roundsig


def ExtendProperties(cls):
    # Add properties to configure the _errorband member histogram of Histo1Ds.
    cls._properties += ["errorband{}".format(p) for p in cls._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Histo1D(MethodProxy, ROOT.TH1D):

    _ignore_properties = ["name", "xtitle", "ytitle", "ztitle"]

    ROOT.TH1.SetDefaultSumw2(True)

    def __init__(self, name, *args, **kwargs):
        MethodProxy.__init__(self)
        self._varexp = None
        self._cuts = None
        self._weight = None
        self._errorband = None
        self._drawoption = ""
        self._drawerrorband = False
        self._addtolegend = True
        self._legenddrawoption = ""
        self._stack = False  # Stack property!
        self._attalpha = defaultdict(lambda: 1.0)
        if len(args) == 1:
            if isinstance(args[0], ROOT.TH1D):
                ROOT.TH1D.__init__(self, args[0].Clone(name))
                self.SetDirectory(0)
            if isinstance(args[0], Histo1D):
                self._varexp = args[0]._varexp
                self._cuts = args[0]._cuts
                self._weight = args[0]._cuts
                self._stack = args[0]._stack
                if args[0]._errorband is not None:
                    self._errorband = Histo1D(
                        "{}_errorband".format(name), args[0]._errorband
                    )
                if not name.endswith("_errorband"):
                    self.DeclareProperties(**args[0].GetProperties())
                    self.DeclareProperties(
                        **args[0]._errorband.GetProperties(prefix="errorband")
                    )
        elif len(args) == 2:
            assert isinstance(args[0], str)
            assert isinstance(args[1], (list, tuple))
            lowbinedges = array("d", args[1])
            ROOT.TH1D.__init__(self, name, args[0], len(lowbinedges) - 1, lowbinedges)
        elif len(args) == 4:
            assert isinstance(args[0], str)
            assert isinstance(args[1], int)
            ROOT.TH1D.__init__(self, name, *args)
        else:
            raise TypeError
        if not name.endswith("_errorband") and self._errorband is None:
            self._errorband = Histo1D("{}_errorband".format(self.GetName()), self)
            for key, value in self.GetTemplate(
                kwargs.get("template", "common")
            ).items():
                kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)
        self._lowbinedges = IOManager._getBinning(self)["xbinning"]
        self._nbins = len(self._lowbinedges) - 1

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
            self._errorband.Reset()
            self._errorband.Add(self)  # making sure the erroband is up-to-date
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
        scale = 1.0 + kwargs.get("ypadding", 0.25)  # Pad property
        logx = kwargs.get("logx", False)
        logy = kwargs.get("logy", False)
        xtitle = kwargs.get("xtitle", None)
        ytitle = kwargs.get("ytitle", "Entries")
        xunits = kwargs.get("xunits", None)
        if xtitle is None:
            xtitle = self._varexp if self._varexp is not None else ""
        binwidths = [roundsig(w, 4, decimals=True) for w in self.GetBinWidths()]
        if len(set(binwidths)) == 1:
            binwidth = (
                int(binwidths[0])
                if binwidths[0].is_integer()
                else round(binwidths[0], 1)
            )
            if not ytitle.endswith((str(binwidth), str(xunits))):
                ytitle += " / {}".format(binwidth)
            if xunits and not ytitle.endswith(xunits):
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
            frame["xmin"] = kwargs.get("xmin", 1e-2)
        if logy:
            frame["ymin"] = kwargs.get("ymin", 1e-2)
            frame["ymax"] = 10 ** (
                scale * ROOT.TMath.Log10(frame["ymax"] / frame["ymin"])
                + ROOT.TMath.Log10(frame["ymin"])
            )
        else:
            frame["ymax"] *= scale
        return frame

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        properties = DissectProperties(kwargs, [Histo1D, Plot, Canvas, Pad])
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Histo1D"], properties["Pad"]))
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def Add(self, histo, scale=1):
        raw_entries = self.GetEntries() + histo.GetEntries()
        super(Histo1D, self).Add(histo, scale)
        self.SetEntries(raw_entries)

    def SetLegendDrawOption(self, option):
        self._legenddrawoption = option

    def GetLegendDrawOption(self):
        return self._legenddrawoption

    def SetLineAlpha(self, alpha):
        self._attalpha["line"] = alpha
        self.SetLineColorAlpha(self.GetLineColor(), alpha)

    def GetLineAlpha(self):
        return self._attalpha["line"]

    def SetFillAlpha(self, alpha):
        self._attalpha["fill"] = alpha
        self.SetFillColorAlpha(self.GetFillColor(), alpha)

    def GetFillAlpha(self):
        return self._attalpha["fill"]

    def SetMarkerAlpha(self, alpha):
        self._attalpha["marker"] = alpha
        self.SetMarkerColorAlpha(self.GetMarkerColor(), alpha)

    def GetMarkerAlpha(self):
        return self._attalpha["marker"]

    def SetLineColor(self, color):
        self.SetLineColorAlpha(color, self._attalpha["line"])

    def SetFillColor(self, color):
        self.SetFillColorAlpha(color, self._attalpha["fill"])

    def SetMarkerColor(self, color):
        self.SetMarkerColorAlpha(color, self._attalpha["marker"])

    def SetAddToLegend(self, boolean):
        self._addtolegend = boolean

    def GetAddToLegend(self):
        return self._addtolegend

    def SetStack(self, boolean):
        """Set how the object is displayed if added to a Stack."""
        self._stack = boolean

    def GetStack(self):
        return self._stack


def main():

    filename = "../data/ds_data18.root"
    h = Histo1D("test", "test", 20, 0.0, 400.0)
    # Histo1D.PrintAvailableProperties()
    h.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    # print(h)
    # print(h.Integral())
    h.Print("test_histo_data.pdf", template="data", logy=False, xunits="GeV")
    h.Print(
        "test_histo_background.pdf", template="background", logy=False, xunits="GeV"
    )
    h2 = Histo1D("test2", h, template="signal", drawerrorband=True)
    h3 = Histo1D("test3", h2, linecolor=ROOT.kGreen)
    h3.Print("test_histo_signal.pdf", logy=True, xunits="GeV")


if __name__ == "__main__":
    main()
