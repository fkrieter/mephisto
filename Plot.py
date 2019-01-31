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
        self._padproperties = defaultdict(dict)
        self._mkdirs = False
        # TODO:
        # * Infer axis ranges before DrawFrame
        # * Helper function to disentangle kwargs and check for unknown ones
        # * set default x/y minimum with respect to log flag

    def Register(self, object, pad=0, **kwargs):
        assert(isinstance(pad, int))
        objectproperties = {k:kwargs.pop(k) for k,v in list(kwargs.items()) if k in
            object.GetListOfProperties() + ["template"]}
        padproperties = {k:kwargs.pop(k) for k,v in list(kwargs.items()) if k in
            Pad.GetListOfProperties()}
        if set(objectproperties.keys()) & set(["xtitle", "ytitle"]):
            padproperties.setdefault("title", ";{};{}".format(
                objectproperties.get("xtitle"), objectproperties.get("ytitle")))
        self._store[pad].append((object, objectproperties))
        self._padproperties[pad].update(padproperties)

    def SetMkdirs(self, boolean):
        self._mkdirs = boolean

    def GetMkdirs(self):
        return self._mkdirs

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        plotproperties = {k:kwargs.pop(k) for k,v in list(kwargs.items()) if k in
            Plot.GetListOfProperties() + ["template"]}
        canvasproperties = {k:kwargs.pop(k) for k,v in list(kwargs.items()) if k in
            Canvas.GetListOfProperties()}
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        npads = len(self._store)
        canvas = Canvas("test", template=str(npads), **canvasproperties)
        for i, store in self._store.items():
            pad = Pad("{}_pad{}".format(canvas.GetName(), i),
                template="{};{}".format(npads, i), **self._padproperties[i])
            pad.DrawFrame(0., 1., 400, 1000.)
            canvas.SetSelectedPad(pad)
            for obj, properties in store:
                with UsingProperties(obj, **properties):
                    obj.Draw(obj.GetDrawOption() + "same")
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
