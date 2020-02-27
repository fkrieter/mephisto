#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from MethodProxy import *


@PreloadProperties
class Line(MethodProxy, ROOT.TLine):

    # Properties not meant to be changed via keyword arguments:
    _ignore_properties = [
        "bboxcenter",
        "bboxcenterx",
        "bboxcentery",
        "bboxx1",
        "bboxx2",
        "bboxy1",
        "bboxy2",
    ]

    def __init__(self, *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TLine.__init__(self, *args)
        self._ndc = False
        if len(args) >= 4:
            kwargs["x1"], kwargs["y1"], kwargs["x2"], kwargs["y2"] = args[0:4]
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def SetNDC(self, boolean):
        self._ndc = boolean
        super(Line, self).SetNDC(boolean)

    def GetUseNDC(self):
        return self._ndc


if __name__ == "__main__":

    from Plot import Plot

    p = Plot()

    a = Line(0.25, 0.25, 0.75, 0.75)

    p.Register(a, logy=False)
    p.Print("test_line.pdf")
