#!/usr/bin/env python2.7

import ROOT

from MethodProxy import *


@PreloadProperties
class Canvas(MethodProxy, ROOT.TCanvas):

    _ignore_properties = ["logx", "logy", "logz"] # exclusive properties of Pad

    def __init__(self, *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TCanvas.__init__(self, *args)
        self.DeclareProperties(**kwargs)
        self.Draw()
        self.cd()

    def GetCanvasSize(self):
        return (float(self.GetWw()), float(self.GetWh()))

    def Delete(self):
        ROOT.gROOT.GetClass(self.__class__.__base__.__name__).Destructor(self)
