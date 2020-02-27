#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import re

from Canvas import Canvas
from MethodProxy import *


@PreloadProperties
class Text(MethodProxy, ROOT.TLatex):

    # Properties not meant to be changed via keyword arguments:
    _ignore_properties = [
        "bboxcenter",
        "bboxcenterx",
        "bboxcentery",
        "bboxx1",
        "bboxx2",
        "bboxy1",
        "bboxy2",
        "mbtitle",
    ]

    def __init__(self, *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TLatex.__init__(self, *args)
        if len(args) == 3:
            kwargs["x"], kwargs["y"] = args[0:2]
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def GetXsize(self):
        xsf = 15.8  # a wild scale factor appears...
        c = ROOT.TCanvas("tmp", "", 100, 100)
        c.Draw()
        self.Draw()
        font = self.GetTextFont()
        with UsingProperties(self, textfont=10 * (font - (font % 10) / 10) + 2):
            size = (self.GetTextSize() / (ROOT.gPad.GetWw() / xsf)) * (
                super(Text, self).GetXsize()
                / (ROOT.gPad.GetWh() * ROOT.gPad.GetWw()) ** 0.5
                / self.GetTextSize()
            )
        return size

    def GetYsize(self, ignoreformulas=True):
        ysf = 13.0  # a wild scale factor appears...
        c = ROOT.TCanvas("tmp", "", 100, 100)
        c.Draw()
        self.Draw()
        font = self.GetTextFont()
        tmptitle = self.GetTitle()
        if ignoreformulas:
            tmptitle = re.sub("[\_\^]{(.*?)}", "", tmptitle)  # remove sub-/superscripts
            for mod in ["bar", "tilde"]:  # remove bar, tilde, ...
                rgx = "[\#]" + mod + "{(.*?)}"
                match = re.search(rgx, tmptitle)
                if match is not None:
                    tmptitle = re.sub(rgx, match.group()[len(mod) + 2 : -1], tmptitle)
        with UsingProperties(
            self, textfont=10 * (font - (font % 10) / 10) + 2, title=tmptitle
        ):
            size = (self.GetTextSize() / (ROOT.gPad.GetWh() / ysf)) * (
                super(Text, self).GetYsize()
                / (ROOT.gPad.GetWh() * ROOT.gPad.GetWw()) ** 0.5
                / self.GetTextSize()
            )
        return size


if __name__ == "__main__":

    from Plot import Plot

    p1 = Plot()
    p2 = Plot(npads=2)
    p3 = Plot(npads=3)

    x_0 = 0.2
    y_0 = 0.5

    logy = False

    # print("PLOT 1 (npads = 1)")
    t1 = Text(x_0, y_0, "TEST 12345")
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(), "TEST 123TT")
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(), "TEST 12345")
    t4 = Text(x_0 + t1.GetXsize(), t1.GetY() - t2.GetYsize(), "TEST 12345")

    p1.Register(t1, logy=logy)
    p1.Register(t2)
    p1.Register(t3)
    p1.Register(t4)
    p1.Print("text_test-1.pdf", luminosity=139)

    # print("PLOT 2 (npads = 2)")
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(), "TEST 123TT")
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(), "TEST 12345")
    t4 = Text(x_0 + t1.GetXsize(), t1.GetY() - t2.GetYsize(), "TEST 12345")

    p2.Register(t1, pad=0, logy=logy)
    p2.Register(t2, pad=0)
    p2.Register(t3, pad=0)
    p2.Register(t4, pad=0)
    p2.Print("text_test-2.pdf", luminosity=139)

    # print("PLOT 2 (npads = 3)")
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(), "TEST 123TT")
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(), "TEST 12345")
    t4 = Text(x_0 + t1.GetXsize(), t1.GetY() - t2.GetYsize(), "TEST 12345")

    p3.Register(t1, pad=0, logy=logy)
    p3.Register(t2, pad=0)
    p3.Register(t3, pad=0)
    p3.Register(t4, pad=0)
    p3.Print("text_test-3.pdf", luminosity=139)
