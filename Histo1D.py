#!/usr/bin/env python2.7

import ROOT

import math
from uuid import uuid4
from array import array

from Plot import Plot
from MethodProxy import *
from iomanager import iomanager


class Histo1D(MethodProxy, ROOT.TH1D):
    def __init__ (self, name="undefined", *args):
        self._drawoption = ""
        MethodProxy.__init__(self)
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
        self._lowbinedges = iomanager._get_binning(self)["xbinning"]

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

    def Print(self, path, **kwargs):
        template = kwargs.pop("template", "signal")
        units = kwargs.pop("units", None)
        drawerrorband = kwargs.pop("drawerrorband", template == "background")
        histoproperties = {k:v for k, v in kwargs.items() if k.lower() in \
            self.GetListOfProperties()}
        histoproperties["template"] = template
        xtitle, ytitle = self.GetXTitle(), self.GetYTitle()
        if units:
            xtitle += " [{}]".format(str(units))
            ytitle += " {}".format(str(units))
        histoproperties.setdefault("xtitle", xtitle)
        histoproperties.setdefault("ytitle", ytitle)
        plot = Plot()
        plotproperties = {k:v for k, v in kwargs.items() if k.lower() in \
            plot.GetListOfProperties()}
        for key in list(histoproperties.keys() + plotproperties.keys()):
            if key in kwargs.keys():
                del kwargs[key]
        if kwargs:
            raise KeyError("Unknown keyword argument(s) '{}'".format(
                ', '.join(kwargs.keys())))
        plot.Register(self, **histoproperties)
        if drawerrorband:
            # TODO: Make errorband configurable via Print()'s kwargs
            errorbandcolor = histoproperties.get("linecolor")
            errorbandcoloralpha = histoproperties.get("linecoloralpha")
            plot.Register(self, template="errorband", fillcolor=errorbandcolor,
                fillcoloralpha=errorbandcoloralpha)
        plot.Print(path, **plotproperties)

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
    h.PrintAvailableProperties()
    h.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    print h
    print h.Integral()
    h.Print("test_histo_data.pdf",
        template="data",
        units="GeV")
    h.Print("test_histo_background.pdf",
        template="background",
        units="GeV")
    h.Print("test_histo_signal.pdf",
        template="signal",
        units="GeV")

if __name__ == '__main__':
    main()
