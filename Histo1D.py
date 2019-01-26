#!/usr/bin/env python2.7

import ROOT

import math
from array import array

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
            elif isinstance(args[0], ROOT.TH1D):
                self = args[0].Clone(name)
        elif len(args) == 3 and isinstance(args[0], int):
            ROOT.TH1D.__init__(self, name, "", *args)
        else:
            raise TypeError
        self.Sumw2()
        self._lowbinedges = iomanager._get_binning(self)

    def Fill(self, filename, **kwargs):
        iomanager.fill_histo(self, filename, **kwargs)

    def SetDrawOption(self, string):
        if not isinstance(string, str) and not isinstance(string, unicode):
            raise Type
        self._drawoption = string
        super(Histo1D, self).SetDrawOption(string)

    def GetDrawOption(self):
        return self._drawoption

    def Draw(self, drawoption=None):
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        super(Histo1D, self).Draw(self.GetDrawOption() + "same")

    def Print(self, path, **kwargs):
        c = ROOT.TCanvas("canvas")
        with UsingProperties(self, **kwargs):
            c.cd()
            self.Draw()
            c.Print(path)
        ROOT.gROOT.GetClass(c.__class__.__name__ ).Destructor(c)
        del c

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
        template="data")
    h.Print("test_histo_background.pdf",
        template="background")

if __name__ == '__main__':
    main()
