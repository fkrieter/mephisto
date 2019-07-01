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
    r"""Class for comparing 1-dimensional histograms.

    +-------------------------------------------------------------------------------+
    | Inherits from :class:`.Histo1D` which inherits from :class:`ROOT.TH1D`, see   |
    | official `documentation <https://root.cern.ch/doc/master/classTH1.html>`_     |
    | as well!                                                                      |
    +-------------------------------------------------------------------------------+

    Compares histograms to a **baseline** by computing the ratio for each bin.

    The properties of the **baseline** (which is itself of type ``Histo1D``) of the
    :class:`.RatioPlot` object can be accessed by prepending the prefix 'baseline' in
    front of the property name.
    """

    def __init__(self, numerator, denominator=0, **kwargs):
        r"""Initialize a ratio plot for 1-dimensional histograms.

        Create an instance of :class:`.RatioPlot` with the specified (list of)
        **numerator** histogram(s) and **denominator** histogram.

        :param numerator: numerator histogram or list thereof
        :type name: ``Histo1D``, ``TH1D``, ``list``

        :param denominator: denominator histogram which will act as the **baseline**
        :type name: ``Histo1D``, ``TH1D``

        :param \**kwargs: :class:`.RatioPlot` properties
        """
        self._loadTemplates()
        self._drawarrows = False
        self._drawbenchmarklines = False
        if isinstance(numerator, list):
            # TODO: Compute and plot multiple at once
            raise NotImplementedError
        assert numerator.InheritsFrom("TH1")
        kwargs.setdefault("template", "common")
        if denominator.InheritsFrom("TH1"):
            super(RatioPlot, self).__init__(
                "{}_RatioPlotNumerator".format(numerator.GetName()), numerator
            )
            self._baseline = Histo1D(
                "{}_RatioPlotDenominator".format(numerator.GetName()), denominator
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
            denominator.InheritsFrom("TFitResult")
            or denominator == 0
            or denominator.InheritsFrom("THStack")
        ):
            raise NotImplementedError
        else:
            raise TypeError
        self.DeclareProperties(**kwargs)

    def Draw(self, drawoption=None):
        # Draw the baseline, its errorband, the numerator histograms and 'out-of-range'
        # arrows.
        self._baseline.Draw(self._baseline.GetDrawOption() + "SAME")  # Histo1D.Draw
        self._baseline.DrawCopy("HIST SAME", "_{}".format(uuid4().hex[:8]))
        if self._drawbenchmarklines:
            self.DrawBenchmarkLines()
        super(RatioPlot, self).Draw(drawoption)
        if self._drawarrows:
            self.DrawArrows()

    def DeclareProperty(self, property, args):
        # Properties starting with "baseline" will be applied to the self._baseline
        # histogram.
        property = property.lower()
        if property.startswith("baseline"):
            self._baseline.DeclareProperty(property[8:], args)
        else:
            super(RatioPlot, self).DeclareProperty(property, args)

    def DrawArrows(self, **kwargs):
        # Draw the 'out-of-range' arrows for ratio value outside the given y-axis range.
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
        # Draw benchmark lines.
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
        r"""Define whether the arrows should be drawn.

        :param boolean: if set to ``True`` arrows will be drawn whenever the ratio is
            outside the given y-axis range
        :type boolean: ``bool``
        """
        self._drawarrows = boolean

    def GetDrawArrows(self):
        r"""Return whether the arrows should be drawn.

        :returntype: ``bool``
        """
        return self._drawarrows

    def SetDrawBenchmarkLines(self, boolean):
        r"""Define whether the benchmark lines should be drawn.

        :param boolean: if set to ``True`` the benchmark lines will be drawn
        :type boolean: ``bool``
        """
        self._drawbenchmarklines = boolean

    def GetDrawBenchmarklines(self):
        r"""Return whether the benchmark lines should be drawn.

        :returntype: ``bool``
        """
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
