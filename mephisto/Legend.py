#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import math

from uuid import uuid4

from MethodProxy import *
from Text import Text
from Helpers import DissectProperties, MergeDicts, MephistofyObject


@PreloadProperties
class Legend(MethodProxy, ROOT.TLegend):
    def __init__(self, name=uuid4().hex[:8], *args, **kwargs):
        MethodProxy.__init__(self)
        ROOT.TLegend.__init__(self, *args)
        self.SetName(name)
        self._store = []
        self._autoncolumns = False
        self._xshift = 0
        self._yshift = 0
        kwargs.setdefault("template", "common")
        self.DeclareProperties(**kwargs)

    def SetAutoNColumns(self, boolean):
        self._autoncolumns = boolean

    def GetAutoNColumns(self):
        return self._autoncolumns

    @MephistofyObject(copy=True)
    def Register(self, histo, **kwargs):
        histo.DeclareProperties(**kwargs)
        self._store.append(histo)

    def Draw(self, option="", **kwargs):
        # self.BuildLegend()  # not here!!!
        for histo in self._store:
            self.AddEntry(histo, histo.GetTitle(), histo.GetLegendDrawOption())
        ROOT.gPad.GetCanvas().cd()  # Draw on canvas instead of pad to avoid some weird
        # horizontal alignment issues...
        super(Legend, self).Draw(option + "SAME")

    def BuildLegend(self):
        if len(self._store) > 4 and self._autoncolumns:
            self.SetNColumns(2)
            if len(self._store) > 12:
                self.SetNColumns(3)
        # TODO: This is where the "magic" should happen in principle... The scaling
        # (long vs. short titles) as well as the horizontal alignment still need some
        # further optimization.
        maxtitlewidth = 0.0
        maxtitleheight = 0.0
        lastcolmaxtitlewidth = 0.0
        for i, histo in enumerate(self._store):
            title = Text(0, 0.5, histo.GetTitle(), textsize=self.GetTextSize())
            maxtitlewidth = max(maxtitlewidth, title.GetXsize())
            if i % 2 == 0:
                maxtitleheight += title.GetYsize()
            elif i % 2 == 1:
                lastcolmaxtitlewidth = max(lastcolmaxtitlewidth, title.GetXsize())
        x2 = 300.0 * (1 + maxtitlewidth - lastcolmaxtitlewidth) + self._xshift
        x1 = max(
            0.52, x2 - (self.GetNColumns() * 0.9 * maxtitlewidth) - self.GetMargin()
        )
        y2 = (
            2.8
            + maxtitleheight
            / (
                (len(self._store) + len(self._store) % self.GetNColumns())
                / self.GetNColumns()
            )
            + self._yshift
        )
        y1 = y2 - (2.5 * maxtitleheight)
        self.DeclareProperties(x1=x1, x2=x2, y1=y1, y2=y2)

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

    l = Legend("test")

    h = {}
    p = Plot()
    for i in range(1, 7, 1):
        h[i] = Histo1D("test_{}".format(i), "title", 20, 0.0, 400.0)
        h[i].Fill(
            filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>6{}0".format(i)
        )
        props = dict(
            template="signal", linecolor=i, title=random.choice(WORDS).capitalize()[:8]
        )
        l.Register(h[i], **props)
        p.Register(h[i], **props)
    l.BuildLegend()
    p.Register(l)
    p.Print("test_legend.pdf")
