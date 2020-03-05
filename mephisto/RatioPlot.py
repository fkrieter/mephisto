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
    # Add properties to configure the _baseline histogram of RatioPlots and add new
    # properties and methods manually since RatioPlot does not inherit from MethodProxy
    # directly.
    cls._properties += ["baseline{}".format(p) for p in Histo1D._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class RatioPlot(MethodProxy):
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

    # Properties not meant to be changed via keyword arguments:
    _ignore_properties = ["name"]

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
        MethodProxy.__init__(self)
        self._name = uuid4().hex[:8]
        self._drawarrows = False
        self._drawbenchmarklines = False
        if not isinstance(numerator, list):
            numerator = [numerator]
        kwargs.setdefault("template", "common")
        if denominator.InheritsFrom("TH1"):
            self._baseline = Histo1D(
                "{}_RatioPlotDenominator".format(denominator.GetName()), denominator
            )
            self._numeratorhistos = []
            for i, histo in enumerate(numerator, start=1):
                assert histo.InheritsFrom("TH1")
                numname = histo.GetName()
                numerator = Histo1D(
                    "{}_RatioPlotNumerator{}".format(denominator.GetName(), i), histo
                )
                numerator.Divide(
                    histo, self._baseline, 1.0, 1.0, kwargs.get("divideoption", "pois")
                )
                self._numeratorhistos.append(numerator)
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
        self._ymin = None
        self._ymax = None
        self._numeratordrawoption = ""
        self.DeclareProperties(**kwargs)

    def Draw(self, option=None):
        # Draw the baseline, its errorband, the numerator histograms and 'out-of-range'
        # arrows. The specified draw option will be used for all numerator histograms.
        self._baseline.Draw(self._baseline.GetDrawOption() + "SAME")  # Histo1D.Draw
        if self._drawbenchmarklines:
            self.DrawBenchmarkLines()
        self.SetDrawOption(option.upper().replace("SAME", ""))
        for numerator in self._numeratorhistos:
            numerator.Draw(numerator.GetDrawOption() + "SAME")
        if self._drawarrows:
            self.DrawArrows()

    def DeclareProperty(self, property, args):
        # Properties starting with "baseline" will be applied to the denominator
        # histogram
        property = property.lower()
        if property.startswith("baseline"):
            self._baseline.DeclareProperty(property[8:], args)
        else:
            # for numerator in self._numeratorhistos:
            #     numerator.DeclareProperty(property, args)
            super(RatioPlot, self).DeclareProperty(property, args)
        pass

    def SetYMin(self, value):
        r"""Set the minimal value of the y-axis.

        :param value: minimal value of the y-axis
        :type value: ``float``
        """
        self._ymin = value

    def GetYMin(self):
        r"""Return the minimal value of the y-axis.

        :returntype: ``float``
        """
        return self._ymin

    def SetYMax(self, value):
        r"""Set the maximal value of the y-axis.

        :param value: maximal value of the y-axis
        :type value: ``float``
        """
        self._ymax = value

    def GetYMax(self):
        r"""Return the maximal value of the y-axis.

        :returntype: ``float``
        """
        return self._ymax

    def BuildFrame(self, **kwargs):
        # Compute optimal x- and y-axis ranges.
        frame = {}
        for histo in self._numeratorhistos:
            if not frame:
                frame = histo.BuildFrame(**kwargs)
            else:
                for key, func in [
                    ("xmin", min),
                    ("ymin", min),
                    ("xmax", max),
                    ("ymax", max),
                ]:
                    frame[key] = func(frame[key], histo.BuildFrame(**kwargs)[key])
        if self._ymin is not None:
            frame["ymin"] = self._ymin
        if self._ymax is not None:
            frame["ymax"] = self._ymax
        return frame

    def DrawArrows(self, **kwargs):
        # Draw the 'out-of-range' arrows for ratio value outside the given y-axis range.
        currentpad = ROOT.gPad
        if not currentpad:
            return
        ymax = currentpad.GetUymax()
        ymin = currentpad.GetUymin()
        self._arrows = []
        for bn in range(1, self._baseline.GetNbinsX() + 1, 1):
            bnclist = [h.GetBinContent(bn) for h in self._numeratorhistos]
            if all([bnc == 0 for bnc in bnclist]):
                continue
            if max(bnclist) > ymax:
                self._arrows.append(
                    Arrow(
                        self._baseline.GetXaxis().GetBinCenter(bn),
                        ymax - (ymax - ymin) * 0.03,
                        self._baseline.GetXaxis().GetBinCenter(bn),
                        ymax - (ymax - ymin) * 0.15,
                        arrowsize=0.01,
                    )
                )
            elif min(bnclist) < ymin:
                self._arrows.append(
                    Arrow(
                        self._baseline.GetXaxis().GetBinCenter(bn),
                        ymin + (ymax - ymin) * 0.03,
                        self._baseline.GetXaxis().GetBinCenter(bn),
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
            if bm < ymin or bm == 1:
                continue
            if bm > ymax:
                break
            self._benchmarklines.append(
                Line(xmin, bm, xmax, bm, linestyle=7, linecoloralpha=(ROOT.kBlack, 0.6))
            )
        for line in self._benchmarklines:
            line.Draw()

    def SetName(self, name):
        r"""Set the name of object.

        :param name: name of the object
        :type name: ``str``
        """
        self._name = name

    def GetName(self):
        r"""Return the name of the object.

        :returntype: ``str``
        """
        return self._name

    def InheritsFrom(self, classname):
        # Dummy function (SensitivityScan does not inherit from any ROOT function)
        return False

    def SetDrawOption(self, option):
        r"""Define the draw option for all numerator histograms.

        :param option: draw option (see :class:`ROOT.THistPainter`
            `class reference <https://root.cern/doc/master/classTHistPainter.html>`_)
        :type option: ``str``
        """
        if option:
            self._numeratordrawoption = option
            for numerator in self._numeratorhistos:
                numerator.SetDrawOption(self._numeratordrawoption)

    def GetDrawOption(self):
        r"""Return the draw option defined for all numerator histograms.

        :returntype: ``str``
        """
        return self._numeratordrawoption

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

    RatioPlot.PrintAvailableProperties()

    h1 = Histo1D("test1", "test1", 20, 0.0, 400.0)
    h2 = Histo1D("test2", "test2", 20, 0.0, 400.0)
    h3 = Histo1D("test3", "test3", 20, 0.0, 400.0)
    h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>620")
    h3.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>700")

    h1.DeclareProperty("template", "background")
    h2.DeclareProperties(template="data", markercolor="#a7126b", linecolor="#a7126b")
    h3.DeclareProperties(template="signal", linecolor="#17a242")
    rp = RatioPlot([h2, h3], h1)

    p1 = Plot(npads=2)
    p1.Register(h1, 0)
    p1.Register(h2, 0, xunits="GeV")
    p1.Register(h3, 0)
    p1.Register(rp, 1, logy=False, ymin=0.5, ymax=2.0, ytitle="Data / Bkg.")
    p1.Print("ratioplot_test.pdf")
