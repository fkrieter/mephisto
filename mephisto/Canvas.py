#!/usr/bin/env python2.7

import ROOT

from MethodProxy import *


@PreloadProperties
class Canvas(MethodProxy, ROOT.TCanvas):

    # Properties not meant to be changed via keyword arguments:
    _ignore_properties = [
        "attfillps",
        "attlineps",
        "attmarkerps",
        "atttextps",
        "bboxcenter",
        "bboxcenterx",
        "bboxcentery",
        "bboxx1",
        "bboxx2",
        "bboxy1",
        "bboxy2",
        "canvas",
        "canvasimp",
        "clickselected",
        "clickselectedpad",
        "fixedaspectratio",
        "maxpickdistance",
        "name",
        "number",
        "pad",
        "padsave",
        "phi",
        "retained",
        "selectedpad",
        "theta",
        "vertical",
        "view",
        "viewer3d",
        "windowposition",
        "windowsize",
        "xfile",
        "xstat",
        "yfile",
        "ystat",
        # Exclusive properties of Pad:
        "logx",
        "logy",
        "logz",
        "topmargin",
        "bottommargin",
        "leftmargin",
        "rightmargin",
    ]

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
