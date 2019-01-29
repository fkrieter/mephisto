#!/usr/bin/env python2.7

import ROOT

from collections import defaultdict

from Pad import Pad
from Canvas import Canvas
from MethodProxy import *
from Helpers import CheckPath


@PreloadProperties
class Plot(MethodProxy):

    def __init__(self):
        MethodProxy.__init__(self)
        self._store = defaultdict(list)
        self._mkdirs = False

    def Register(self, object, pad=0, **kwargs):
        self._store[pad].append((object, kwargs))

    def SetMkdirs(self, boolean):
        self._mkdirs = boolean

    def GetMkdirs(self):
        return self._mkdirs

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        npads = len(self._store)
        canvas = Canvas("test", template=str(npads))
        for i, objects in self._store.items():
            pad = Pad("{}_pad{}".format(canvas.GetName(), i),
                template="{};{}".format(npads, i))
            canvas.SetSelectedPad(pad)
            suffix = ""
            for obj, properties in self._store[0]:
                with UsingProperties(obj, **properties):
                    obj.Draw(obj.GetDrawOption() + suffix)
                suffix = "same"
                # legend = pad.BuildLegend()
                # legend.Draw(suffix)
        canvas.Print(path)
        logger.info("Created plot: '{}'".format(path))
        canvas.Delete()



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
