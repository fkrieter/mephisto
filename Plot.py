#!/usr/bin/env python2.7

import ROOT

from collections import defaultdict

from Pad import Pad
from MethodProxy import *


class Plot(object):

    def __init__(self):
        self._store = defaultdict(list)

    def Register(self, object, pad=0, **kwargs):
        self._store[pad].append((object, kwargs))

    def Print(self, path):
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        canvas = ROOT.TCanvas("test")
        canvas.SetFillStyle(4000) # transparent background
        canvas.Draw()
        canvas.cd()
        pads = []
        npads = len(self._store)
        for i, objects in self._store.items():
            pads.append(Pad("{}_pad{}".format(canvas.GetName(), i)))
            pad = pads[i]
            pad.DeclareProperties(template="{};{}".format(npads, i))
            pad.Draw()
            pad.cd()
            canvas.SetSelectedPad(pad)
            suffix = ""
            for obj, properties in self._store[0]:
                with UsingProperties(obj, **properties):
                    obj.Draw(obj.GetDrawOption() + suffix)
                suffix = "same"
        canvas.Print(path)
        ROOT.gROOT.GetClass(canvas.__class__.__name__ ).Destructor(canvas)
        del canvas



if __name__ == '__main__':

    from Histo1D import Histo1D

    filename = "data/ds_data18.root"
    h1 = Histo1D("test1", 20, 0., 400.)
    h2 = Histo1D("test2", 20, 0., 400.)
    h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>750")

    p = Plot()
    p.Register(h1, 0, template="background")
    p.Register(h2, 0, template="signal")
    p.Print("plot_test.pdf")
