#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import math

from uuid import uuid4

from Text import Text
from MethodProxy import *
from Helpers import DissectProperties, MergeDicts, MephistofyObject


@PreloadProperties
class Legend(MethodProxy, ROOT.TLegend):
    def __init__(self, name=uuid4().hex[:8], *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TLegend.__init__(self, *args)
        if len(args) >= 4:
            kwargs["x1"], kwargs["y1"], kwargs["x2"], kwargs["y2"] = args[0:4]
        self.SetName(name)
        self._store = []
        self._autoncolumns = False
        self._xshift = 0
        self._yshift = 0
        self._maxwidht = 0.5
        self._entrysorting = None
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def SetAutoNColumns(self, boolean):
        self._autoncolumns = boolean

    def GetAutoNColumns(self):
        return self._autoncolumns

    @MephistofyObject(copy=True)
    def Register(self, histo, **kwargs):
        if histo.InheritsFrom("THStack"):
            for h in histo.GetHists():
                if h.GetAddToLegend():
                    self._store.append(h)
        else:
            histo.DeclareProperties(**kwargs)
            if histo.GetAddToLegend():
                self._store.append(histo)

    def Draw(self, option="", **kwargs):
        for histo in self._store:
            self.AddEntry(histo, histo.GetTitle(), histo.GetLegendDrawOption())
        self.BuildFrame()
        # Scaling (keep Legend frame independent of pad/canvas aspect ratio)
        cpad = ROOT.gPad  # current pad
        canvasheight = cpad.GetCanvas().GetWh() * cpad.GetCanvas().GetAbsHNDC()
        canvaswidth = cpad.GetCanvas().GetWw() * cpad.GetCanvas().GetAbsWNDC()
        padheight = cpad.GetWh() * cpad.GetAbsHNDC()
        xscale = 700.0 / canvaswidth
        yscale = canvaswidth / canvasheight
        yscale *= canvasheight / padheight
        yscale *= 700.0 / canvaswidth
        height = self.GetY2() - self.GetY1()
        self.SetX1(self.GetX2() - ((self.GetX2() - self.GetX1()) * xscale))
        self.SetY1(self.GetY2() - ((self.GetY2() - self.GetY1()) * yscale))
        super(Legend, self).Draw(option + "SAME")

    def GetNRows(self):
        return (
            len(self._store) / self.GetNColumns()
            + len(self._store) % self.GetNColumns()
        )

    def SetMaxWidth(self, value):
        self._maxwidth = value

    def GetMaxWidth(self):
        return self._maxwidth

    def AddEntrySortingProperty(self, property, reverse=False):
        if self._entrysorting is None:
            self._entrysorting = []
        self._entrysorting.append((property, reverse))

    def SetEntrySorting(self, *listoftuples):
        for property, reverse in listoftuples:
            self.AddEntrySortingProperty(property, reverse)

    def GetEntrySorting(self):
        return self._entrysorting

    def SortEntries(self):
        from Histo1D import Histo1D

        if self._entrysorting is not None:
            for prop, reverse in reversed(self._entrysorting):
                if prop in [m.lower() for m in Histo1D._properties]:
                    self._store.sort(key=lambda h: h.GetProperty(prop), reverse=reverse)
                else:
                    try:
                        self._store.sort(
                            key=lambda h: getattr(h, prop.capitalize())(),
                            reverse=reverse,
                        )
                    except AttributeError:
                        logger.error(
                            "Sorting failed: 'Histo1D' has no attribute '{}'!".format(
                                prop.capitalize()
                            )
                        )
                        raise AttributeError

    def BuildFrame(self, **kwargs):
        self.SortEntries()
        if len(self._store) > 4 and self._autoncolumns:
            self.SetNColumns(2)
        # TODO: Add top-left, bottom-left and bottom-right alignement.
        maxtitlewidth = 0.0
        maxtitleheight = 0.0
        lastcolmaxtitlewidth = 0.0
        for i, histo in enumerate(self._store):
            title = Text(0.5, 0.5, histo.GetTitle(), textsize=self.GetTextSize())
            maxtitlewidth = max(maxtitlewidth, title.GetXsize())
            maxtitleheight = max(maxtitleheight, title.GetYsize())
            if self.GetNColumns() > 1 and i % self.GetNColumns() == 1:
                lastcolmaxtitlewidth = max(lastcolmaxtitlewidth, title.GetXsize())
        x2 = 0.925 + self._xshift
        x1 = (
            max(
                x2 - self._maxwidth,
                x2
                - max(
                    self.GetNColumns()
                    * (1.5 * (self.GetTextSize() / 700.0) + maxtitlewidth),
                    self.GetMargin() / 1.6,
                ),
            )
            + self._xshift
        )
        y2 = 0.955 + self._yshift
        y1 = y2 - (1.2 * self.GetNRows() * maxtitleheight) + self._yshift
        self.DeclareProperties(x1=x1, y1=y1, x2=x2, y2=y2)

    def SetXShift(self, shift):
        self._xshift = shift

    def GetXShift(self):
        return self._xshift

    def SetYShift(self, shift):
        self._yshift = shift

    def GetYShift(self):
        return self._yshift


if __name__ == "__main__":

    import random

    from Plot import Plot
    from Histo1D import Histo1D

    word_file = "/usr/share/dict/words"
    WORDS = open(word_file).read().splitlines()

    filename = "../data/ds_data18.root"

    # l = Legend("test")

    nentries = 8

    h = {}
    p = Plot()
    for i in range(1, nentries + 1, 1):
        h[i] = Histo1D("test_{}".format(i), "title", 20, 0.0, 400.0)
        h[i].Fill(
            filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>4{}0".format(i)
        )
        props = dict(
            template="signal", linecolor=i, title=random.choice(WORDS).capitalize()[:8]
        )
        # l.Register(h[i], **props)
        p.Register(h[i], **props)
    # l.SetFillColorAlpha(ROOT.TColor.GetColor("#f5a2ff"), 0.3)
    # p.Register(l)
    p.Print("test_legend.pdf")
