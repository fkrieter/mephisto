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

    def GetXsize(self, **kwargs):
        ndc = kwargs.pop("ndc", False)
        scale = kwargs.pop("scale", 1.0)
        if kwargs:
            logger.error(
                "Unknown key word argument(s): '{}'".format(
                    "', '".join(kwargs.values())
                )
            )
        self.Draw()
        norm = ROOT.gPad.GetWw() if ndc else 1.0
        norm *= scale ** 0.7  # wild exponent appeared...
        return super(Text, self).GetXsize() * self.GetTextSize() / (16.0 * norm)

    def GetYsize(self, **kwargs):
        ndc = kwargs.pop("ndc", False)
        scale = kwargs.pop("scale", 1.0)
        if kwargs:
            logger.error(
                "Unknown key word argument(s): '{}'".format(
                    "', '".join(kwargs.values())
                )
            )
        self.Draw()
        norm = ROOT.gPad.GetWh() if ndc else 1.0
        norm *= scale ** 0.7  # wild exponent appeared...
        return super(Text, self).GetYsize() * self.GetTextSize() / (16.0 * norm)


if __name__ == "__main__":

    from Plot import Plot

    p1 = Plot()
    p2 = Plot(npads=2)
    p3 = Plot(npads=3)

    x_0 = 0.5
    y_0 = 0.5

    print("PLOT 1 (npads = 1)")
    t1 = Text(x_0, y_0, "TEST 12345")
    print(t1.GetY())
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(scale=p1.GetPadHeight(0)), "TEST 12345")
    print(t2.GetY())
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(scale=p1.GetPadHeight(0)), "TEST 12345")
    print(t3.GetY())
    t4 = Text(
        x_0 + t1.GetXsize(scale=p1.GetPadWidth(0)),
        t1.GetY() - t2.GetYsize(scale=p1.GetPadHeight(0)),
        "TEST 12345",
    )

    p1.Register(t1)
    p1.Register(t2)
    p1.Register(t3)
    p1.Register(t4)
    p1.Print("text_test-1.pdf")

    print("PLOT 2 (npads = 2)")
    print(t1.GetY())
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(scale=p2.GetPadHeight(0)), "TEST 12345")
    print(t2.GetY())
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(scale=p2.GetPadHeight(0)), "TEST 12345")
    print(t3.GetY())

    p2.Register(t1, pad=0)
    p2.Register(t2, pad=0)
    p2.Register(t3, pad=0)
    p2.Print("text_test-2.pdf")

    print("PLOT 2 (npads = 3)")
    print(t1.GetY())
    t2 = Text(x_0, t1.GetY() - t1.GetYsize(scale=p3.GetPadHeight(0)), "TEST 12345")
    print(t2.GetY())
    t3 = Text(x_0, t2.GetY() - t2.GetYsize(scale=p3.GetPadHeight(0)), "TEST 12345")
    print(t3.GetY())

    p3.Register(t1, pad=0)
    p3.Register(t2, pad=0)
    p3.Register(t3, pad=0)
    p3.Print("text_test-3.pdf")
