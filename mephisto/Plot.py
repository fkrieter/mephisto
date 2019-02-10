#!/usr/bin/env python2.7

import ROOT

from collections import defaultdict

from Pad import Pad
from Canvas import Canvas
from MethodProxy import *
from Helpers import CheckPath, DissectProperties


@PreloadProperties
class Plot(MethodProxy):

    def __init__(self):
        MethodProxy.__init__(self)
        self._store = defaultdict(list)
        self._padproperties = defaultdict(dict)
        self._mkdirs = False
        self._style = "Classic"

    def Register(self, object, pad=0, **kwargs):
        assert(isinstance(pad, int))
        properties = DissectProperties(kwargs, [object, Pad])
        objclsname = object.__class__.__name__
        if set(properties[objclsname].keys()) & set(["xtitle", "ytitle"]):
            properties["Pad"].setdefault("title", ";{};{}".format(
                properties[objclsname].get("xtitle"),
                properties[objclsname].get("ytitle")))
        self._store[pad].append((object, properties[objclsname]))
        self._padproperties[pad].update(properties["Pad"])

    def SetMkdirs(self, boolean):
        self._mkdirs = boolean

    def GetMkdirs(self):
        return self._mkdirs

    def SetStyle(self, style):
        self._style = style
        ROOT.gROOT.SetStyle(style)

    def GetStyle(self):
        return self._style

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        properties = DissectProperties(kwargs, [Plot, Canvas])
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        npads = len(self._store)
        canvas = Canvas("test", template=str(npads), **properties["Canvas"])
        for i, store in self._store.items():
            pad = Pad("{}_pad{}".format(canvas.GetName(), i),
                template="{};{}".format(npads, i), **self._padproperties[i])
            pad.DrawFrame()
            canvas.SetSelectedPad(pad)
            for obj, properties in store:
                with UsingProperties(obj, **properties):
                    obj.Draw(obj.GetDrawOption() + "same")
                # legend = pad.BuildLegend()
                # legend.Draw(suffix)
            pad.RedrawAxis()
        canvas.Print(path)
        logger.info("Created plot: '{}'".format(path))
        canvas.Delete()



if __name__ == '__main__':

    from Histo1D import Histo1D

    filename = "../data/ds_data18.root"
    h1 = Histo1D("test1", 20, 0., 400.)
    h2 = Histo1D("test2", 20, 0., 400.)
    h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>750")

    p = Plot()
    p.Register(h1, 0, template="background")
    p.Register(h2, 0, template="signal")
    p.Print("plot_test.pdf")
