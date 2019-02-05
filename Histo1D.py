#!/usr/bin/env python2.7

import ROOT

import math
from uuid import uuid4
from array import array

from Pad import Pad
from Plot import Plot
from MethodProxy import *
from Canvas import Canvas
from iomanager import iomanager
from Helpers import DissectProperties, MergeDicts


@PreloadProperties
class Histo1D(MethodProxy, ROOT.TH1D):

    def __init__ (self, name="undefined", *args, **kwargs):
        MethodProxy.__init__(self)
        self._drawoption = ""
        self._drawerrorband = False
        if len(args) == 1:
            if isinstance(args[0], list):
                lowbinedges = array("d", args[0])
                ROOT.TH1D.__init__(self, name, "", len(lowbinedges)-1, lowbinedges)
            elif isinstance(args[0], ROOT.TH1D) or isinstance(args[0], Histo1D):
                ROOT.TH1D.__init__(self, args[0].Clone(name))
                self.SetDirectory(0)
        elif len(args) == 3 and isinstance(args[0], int):
            ROOT.TH1D.__init__(self, name, "", *args)
        else:
            raise TypeError
        self.Sumw2()
        self.DeclareProperties(**kwargs)
        self._lowbinedges = iomanager._get_binning(self)["xbinning"]
        self._nbins = len(self._lowbinedges) - 1

    def Fill(self, filename, **kwargs):
        iomanager.fill_histo(self, filename, **kwargs)
        self._setDefaultsAxisTitles(varexp=kwargs.get("varexp"))

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

    def _setDefaultsAxisTitles(self, **kwargs):
        self.SetXTitle(kwargs.get("varexp", ""))
        ytitle = "Entries"
        binwidths = list(set([self._lowbinedges[i+1] - self._lowbinedges[i] for i in \
            range(len(self._lowbinedges) - 1)]))
        if len(binwidths) != 1:
            self.SetYTitle(self._ytitle)
        else:
            binwidth = binwidths[0]
            self.SetYTitle("{} / {}".format(ytitle, int(binwidth) if \
                binwidth.is_integer() else round(binwidth, 1)))

    def _getDefaultPadFrame(self, **kwargs):
        template = kwargs.get("template", "1;0")
        scale = kwargs.get("scale", 1.2) # default: frame is 20% higher than maximum
        frame = {
            "xmin": self._lowbinedges[0], "xmax": self._lowbinedges[self._nbins],
            "ymin": 0.0, "ymax": self.GetMaximum()
        }
        if kwargs.get("logx", Pad.GetTemplate(template)["logx"]):
            frame["xmin"] = 1e-2
        if kwargs.get("logy", Pad.GetTemplate(template)["logy"]):
            frame["ymin"] = 1e-2
            frame["ymax"] = 10**(scale*math.log10(10**(math.log10(frame["ymax"]) - \
                math.log10(frame["ymin"]))) + math.log10(frame["ymin"]))
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
        properties["Pad"].update(self._getDefaultPadFrame(template="1;0",
            **properties["Pad"]))
        plot = Plot()
        plot.Register(self, **MergeDicts(properties["Histo1D"], properties["Pad"]))
        if properties["Histo1D"].get("drawerrorband", \
            self.GetTemplate(properties["Histo1D"]["template"])["drawerrorband"]):
            errorbandcolor = properties["Histo1D"].get("linecolor")
            errorbandcoloralpha = properties["Histo1D"].get("linecoloralpha")
            plot.Register(self, template="errorband", fillcolor=errorbandcolor,
                fillcoloralpha=errorbandcoloralpha, **properties["Pad"])
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def Add(self, histo, scale=1):
        raw_entries = self.GetEntries() + histo.GetEntries()
        super(Histo1D, self).Add(histo, scale)
        self.SetEntries(raw_entries)

    def SetBinLabel(self, index, label, **kwargs):
        scale = kwargs.pop("scale", 1.0)
        option = kwargs.pop("option", "h")
        if kwargs:
            raise KeyError("Unknown keyword argument(s) '{}'".format(
                ', '.join(kwargs.keys())))
        xaxis = self.GetXaxis()
        xaxis.SetLabelSize(xaxis.GetLabelSize() * scale )
        xaxis.SetBinLabel(index, label)
        self.LabelsOption(option)



def main():

    filename = "data/ds_data18.root"
    h = Histo1D("test", 20, 0., 400.)
    Histo1D.PrintAvailableProperties()
    h.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    print h
    print h.Integral()
    h.Print("test_histo_data.pdf",
        template="data",
        units="GeV",
        logy=False)
    h.Print("test_histo_background.pdf",
        template="background",
        units="GeV",
        logy=False)
    h.Print("test_histo_signal.pdf",
        template="signal",
        units="GeV",
        logy=True)

if __name__ == '__main__':
    main()
