#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4

from Histo1D import Histo1D
from MethodProxy import *
from Helpers import DissectProperties, MergeDicts


def ExtendProperties(cls):
    # Add properties to configure the _baseline member histogram of RatioPlots.
    cls._properties += ["baseline{}".format(p) for p in cls._properties]  # append!
    return cls


@ExtendProperties
class RatioPlot(Histo1D):
    def __init__(self, num, denom=0, **kwargs):
        self._loadTemplates()
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
        super(RatioPlot, self).Draw(drawoption)

    def DeclareProperty(self, property, args):
        property = property.lower()
        if property.startswith("baseline"):
            self._baseline.DeclareProperty(property[8:], args)
        else:
            super(RatioPlot, self).DeclareProperty(property, args)


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
