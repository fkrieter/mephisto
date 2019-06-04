#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4

from Line import Line
from Arrow import Arrow
from Histo1D import Histo1D
from MethodProxy import *
from Helpers import DissectProperties, MergeDicts, IsInherited


def ExtendProperties(cls):
    # Add properties to configure the _baseline member histogram of RatioPlots and add
    # new properties and methods manually since RatioPlot does not inherit from
    # MethodProxy directly.
    cls._properties += ["baseline{}".format(p) for p in cls._properties]  # append!
    for setter in [
        f for f in dir(cls) if f.startswith("Set") and callable(getattr(cls, f))
    ]:
        if not IsInherited(cls, setter):
            cls._properties.append(setter[3:].lower())
            cls._methods.append(setter)
    return cls


@ExtendProperties
class RatioPlot(Histo1D):
    def __init__(self, num, denom=0, **kwargs):
        self._loadTemplates()
        self._drawarrows = False
        self._drawbenchmarklines = False
        assert num.InheritsFrom("TH1")
        kwargs.setdefault("template", "common")
        if denom.InheritsFrom("TH1"):
            super(RatioPlot, self).__init__(
                "{}_RatioPlotNumerator".format(num.GetName()), num
            )
            self._baseline = Histo1D(
                "{}_RatioPlotDenominator".format(num.GetName()), denom
            )
            self.Divide(
                self, self._baseline, 1.0, 1.0, kwargs.get("divideoption", "pois")
            )
            for bn in range(self._baseline.GetNbinsX() + 2):
                try:
                    self._baseline.SetBinError(
                        bn,
                        self._baseline.GetBinError(bn)
                        / self._baseline.GetBinContent(bn),
                    )
                except ZeroDivisionError:
                    self._baseline.SetBinError(bn, 0.0)
                self._baseline.SetBinContent(bn, 1.0)
        elif (
            denom.InheritsFrom("TFitResult")
            or denom == 0
            or denom.InheritsFrom("THStack")
        ):
            raise NotImplementedError
        else:
            raise TypeError
        self.DeclareProperties(**kwargs)

    def Draw(self, drawoption=None):
        self._baseline.Draw(self._baseline.GetDrawOption() + "SAME")  # Histo1D.Draw
        self._baseline.DrawCopy("HIST SAME", "_{}".format(uuid4().hex[:8]))
        if self._drawbenchmarklines:
            self.DrawBenchmarkLines()
        super(RatioPlot, self).Draw(drawoption)
        if self._drawarrows:
            self.DrawArrows()

    def DeclareProperty(self, property, args):
        property = property.lower()
        if property.startswith("baseline"):
            self._baseline.DeclareProperty(property[8:], args)
        else:
            super(RatioPlot, self).DeclareProperty(property, args)

    def DrawArrows(self, **kwargs):
        currentpad = ROOT.gPad
        if not currentpad:
            return
        ymax = currentpad.GetUymax()
        ymin = currentpad.GetUymin()
        self._arrows = []
        for bn in range(1, self.GetNbinsX() + 1, 1):
            if self.GetBinContent(bn) == 0.0:
                continue
            sign = -1 if self.GetBinContent(bn) > ymax else 1
            if self.GetBinContent(bn) == 0.0:
                continue
            if self.GetBinContent(bn) > ymax:
                self._arrows.append(
                    Arrow(
                        self.GetXaxis().GetBinCenter(bn),
                        ymax - (ymax - ymin) * 0.03,
                        self.GetXaxis().GetBinCenter(bn),
                        ymax - (ymax - ymin) * 0.15,
                        arrowsize=0.01,
                    )
                )
            elif self.GetBinContent(bn) < ymin:
                self._arrows.append(
                    Arrow(
                        self.GetXaxis().GetBinCenter(bn),
                        ymin + (ymax - ymin) * 0.03,
                        self.GetXaxis().GetBinCenter(bn),
                        ymin + (ymax - ymin) * 0.17,
                        arrowsize=0.01,
                    )
                )
        for arrow in self._arrows:
            arrow.Draw()

    def DrawBenchmarkLines(self):
        currentpad = ROOT.gPad
        if not currentpad:
            return
        xmin = currentpad.GetUxmin()
        xmax = currentpad.GetUxmax()
        ymin = currentpad.GetUymin()
        ymax = currentpad.GetUymax()
        self._benchmarklines = []
        for bm in [i * 0.1 for i in range(-5, 41, 5)]:
            if bm < ymin:
                continue
            if bm > ymax:
                break
            self._benchmarklines.append(
                Line(xmin, bm, xmax, bm, linestyle=7, linecoloralpha=(ROOT.kBlack, 0.6))
            )
        for line in self._benchmarklines:
            line.Draw()

    def SetDrawArrows(self, boolean):
        self._drawarrows = boolean

    def GetDrawArrows(self):
        return self._drawarrows

    def SetDrawBenchmarkLines(self, boolean):
        self._drawbenchmarklines = boolean

    def GetDrawBenchmarklines(self):
        return self._drawbenchmarklines


if __name__ == "__main__":

    from Plot import Plot
    from IOManager import IOManager

    filename = "../data/ds_data18.root"

    h1 = Histo1D("test1", "", 20, 0.0, 400.0)
    h2 = Histo1D("test2", "", 20, 0.0, 400.0)
    h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>620")

    h1.DeclareProperty("template", "background")
    h2.DeclareProperty("template", "data")
    rp = RatioPlot(h2, h1)

    p1 = Plot(npads=2)
    p1.Register(h1, 0)
    p1.Register(h2, 0, xunits="GeV")
    p1.Register(rp, 1, logy=False, ymin=0.5, ymax=2, ytitle="Data / Bkg.")
    p1.Print("ratioplot_test.pdf")
