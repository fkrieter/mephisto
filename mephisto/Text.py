#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from MethodProxy import *


@PreloadProperties
class Text(MethodProxy, ROOT.TLatex):
    def __init__(self, *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TLatex.__init__(self, *args)
        if len(args) == 3:
            kwargs["x"], kwargs["y"] = args[0:2]
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def GetXsize(self, ndc=False):
        self.Draw()
        norm = ROOT.gPad.GetWw() if ndc else 1.0
        return super(Text, self).GetXsize() * 0.95 * self.GetTextSize() / (16.0 * norm)

    def GetYsize(self, ndc=False):
        self.Draw()
        norm = ROOT.gPad.GetWh() if ndc else 1.0
        return super(Text, self).GetYsize() * 0.95 * self.GetTextSize() / (16.0 * norm)
