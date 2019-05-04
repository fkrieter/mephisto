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
        self._maxwidht = 0.5
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
        for histo in self._store:
            self.AddEntry(histo, histo.GetTitle(), histo.GetLegendDrawOption())
        # ROOT.gPad.GetCanvas().cd()
        super(Legend, self).Draw(option + "SAME")

    def GetNRows(self):
        return math.ceil(len(self._store) / self.GetNColumns())

    def SetMaxWidth(self, value):
        self._maxwidth = value

    def GetMaxWidth(self):
        return self._maxwidth

    def BuildFrame(self, **kwargs):
        if len(self._store) > 4 and self._autoncolumns:
            self.SetNColumns(2)
        # TODO: This is where the "magic" should happen in principle... The scaling
        # (long vs. short titles) as well as the horizontal alignment still need some
        # further optimization.
        # WARNING: The following is a complete mess! The resulting legends look okay for
        # now, but that's not a stable solution. Somehow Histo1D and TH1D title scale
        # differently and the number of columns also seems to have an impact on the
        # title's textwidth... brun, couet what's happening here?! x_X
        maxtitlewidth = 0.0
        maxtitleheight = 0.0
        lastcolmaxtitlewidth = 0.0
        nastyfix = False  # yes, that's what it is.
        for i, histo in enumerate(self._store):
            if self.GetNColumns() == 1:
                if "mephistofied" in histo.GetName():
                    nastyfix = True
                    reftextsize = 0.225
                else:
                    reftextsize = 6.5
            else:
                if "mephistofied" in histo.GetName():
                    nastyfix = True
                    reftextsize = 0.13
                else:
                    reftextsize = 4.0
            title = Text(0, 0.5, histo.GetTitle(), textsize=reftextsize)
            maxtitlewidth = max(maxtitlewidth, title.GetXsize())
            if i % self.GetNColumns() == 0:
                maxtitleheight += title.GetYsize()
            elif self.GetNColumns() > 1 and i % self.GetNColumns() == 1:
                lastcolmaxtitlewidth = max(lastcolmaxtitlewidth, title.GetXsize())
        nastywidthscale = 1.0
        if self.GetNColumns() == 1:
            if nastyfix:
                nastywidthscale = 1.0
            else:
                nastywidthscale = 0.028
        else:
            if nastyfix:
                nastywidthscale = 5.0
            else:
                nastywidthscale = 0.059
        maxtitlewidth *= nastywidthscale
        x2 = 0.925 + self._xshift
        x1 = (
            max(
                x2 - self._maxwidth,
                x2
                - max(
                    self.GetNColumns() * 0.95 * maxtitlewidth, self.GetMargin() / 1.6
                ),
            )
            + self._xshift
        )
        y2 = 0.885 + self._yshift
        y1 = y2 - (1.3 * self.GetNColumns() * maxtitleheight) + self._yshift
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

    # l = Legend("test")

    h = {}
    p = Plot()
    for i in range(1, 8 + 1, 1):
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
