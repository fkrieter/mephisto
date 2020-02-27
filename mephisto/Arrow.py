#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from MethodProxy import *


@PreloadProperties
class Arrow(MethodProxy, ROOT.TArrow):

    _ignore_properties = [
        "bboxcenter",
        "bboxcenterx",
        "bboxcentery",
        "bboxx1",
        "bboxx2",
        "bboxy1",
        "bboxy2",
        "bit",
        "dtoronly",
        "objectstat",
        "uniqueid",
    ]

    def __init__(self, *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TArrow.__init__(self, *args)
        self._ndc = False
        if len(args) >= 4:
            kwargs["x1"], kwargs["y1"], kwargs["x2"], kwargs["y2"] = args[0:4]
            if len(args) >= 5:
                kwargs["arrowsize"] = args[4]
                if len(args) == 6:
                    kwargs["option"] = args[5]
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def SetNDC(self, boolean):
        self._ndc = boolean
        super(Arrow, self).SetNDC(boolean)

    def GetUseNDC(self):
        return self._ndc


if __name__ == "__main__":

    from Plot import Plot

    p = Plot()

    a = Arrow(0.25, 0.25, 0.75, 0.75)

    p.Register(a, logy=False)
    p.Print("test_arrow.pdf")
