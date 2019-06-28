#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4

from Line import Line
from Histo1D import Histo1D
from MethodProxy import *
from Helpers import AsymptoticFormulae


@PreloadProperties
class SensitivityScan(MethodProxy):
    """Class for computing the sensitivity that would result from a cut placed at any
    given bin.

    Creates histograms showing the sensitivity scan across all bins for each of the
    specified signal histograms.
    """

    def __init__(self, sighistos, bkghisto, **kwargs):
        """Constructor.

        Creates sensitivity histograms for each of the signal histograms 'sighistos'.
        The sensitivity per bin is computed using the function specified by the
        'sensitivitymeasure' property by comparing the signal yield to the number of
        events in the background histograms 'bkghisto' as defined by the user.

        :param sighistos: a single or list of signal histograms, or list of tuples where
        the first entry corresponds to the signal histogram and the second to the
        dictionary of properties of the resulting sensitivity histogram
        :type sighistos: list, :class:`Histo1D` or ROOT.TH1D

        :param bkghisto: total background histogram
        :type bkghisto: :class:`Histo1D` or ROOT.TH1D

        :param \**kwargs: class properties, see below

        :Keyword Arguments: See properties of :class:`.SensitivityScan`
        """
        self._loadTemplates()
        self._name = "SensitivityScan_{}".format(uuid4().hex[:8])
        self._direction = None
        self._bkghisto = bkghisto
        self._sighistos = []
        properties = []
        if isinstance(sighistos, (list, tuple)):
            for i, entry in enumerate(sighistos):
                if isinstance(entry, (list, tuple)):
                    histo, props = entry
                    self._sighistos.append(histo)
                    properties.append(props)
                else:
                    self._sighistos.append(entry)
                    properties.append({})
        else:
            self._sighistos = [sighistos]
        self._sensitivityhistos = []  # histos to be drawn
        for i, sighisto in enumerate(self._sighistos):
            # Use the same properties as the signal histo:
            scan = Histo1D("{}_SensitivityScan".format(sighisto.GetName()), sighisto)
            scan.Reset()
            self._sensitivityhistos.append(scan)
            self.SetSensitivityHistoProperties(i, **properties[i])
        self._nbins = self._bkghisto.GetNbinsX()
        self._flatbkgsys = 0.0  # relative uncertainty
        self._ymin = None
        self._ymax = None
        self._sensitivitymeasure = None
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)
        self.BuildHistos()

    def SetSensitivityHistoProperties(self, i=0, **kwargs):
        """Declare properties of the sensitivity histogram.

        The parameters 'idx' refers to the sensitivity histogram corresponding to the
        signal histogram with index 'idx' as initially given to the the constructor.

        :param idx: index of the associated signal histogram (default: 0)
        :type idx: int

        :param \**kwargs: histogram properties, see below

        :Keyword Arguments: See properties of :class:`.Histo1D`
        """
        self._sensitivityhistos[i].DeclareProperties(**kwargs)

    def SetDirection(self, sign):
        """Set the direction of the scan.

        For '+' the sensitivity is computed by summing up all entries in current and
        following bins, for '-' in the current and all previous bins.

        :param sign: scan direction, can be either '+' or '-'
        :type sign: str
        """
        assert sign in ["+", "-"]
        self._direction = {"+": 1, "-": -1}.get(sign)

    def GetDirection(self):
        """Returns the direction of the scan."""
        return {1: "+", -1: "-"}.get(self._direction)

    def SetSensitivityMeasure(self, func):
        """Define a function to be used for computing the sensitivity.

        Can be a either a function or lambda taking exactly three parameters or a string
        containing the code to be executed. The three parameters are 's', 'b' and 'db'
        which will be interpreted then as:
          * s : number of signal events
          * b : number of background events
          * db : total relative background uncertainty (including 'flatbkgsys')

        Examples:
          * func = lambda s, b, db : s / b
          * func = 's / b'
          * func = ROOT.RooStats.NumberCountingUtils.BinomialExpZ(s, b, db)
          * func = 'AsymptoticFormulae.AsimovExpZ(s, b, db)'

        :param func: function or string of code used to evaluate the sensitivity
        :type func: function or str
        """
        if isinstance(func, (str, unicode)):
            self._sensitivitymeasure = lambda s, b, db: eval(func)
        elif func.__code__.co_argcount != 3:
            logger.error(
                "Sensitivity measure must be a function with three arguments, "
                "the first and second representing number of signal and background "
                "events, respectively, and the last the total relative background "
                "uncertainty. E.g.: lambda s, b, db : s / b"
            )
            raise TypeError
        else:
            self._sensitivitymeasure = func
        try:
            self._sensitivitymeasure(1, 1, 1)
        except NameError:
            logger.error(
                "Allowed parameters names for sensitivity measure are 's' ("
                "number of signal events), 'b' (number of background events) and 'db' ("
                "total relative background uncertainty)"
            )
            raise NameError

    def GetSensitivityMeasure(self):
        """Return the function used to evaluate the sensitivity."""
        return self._sensitivitymeasure

    def SetName(self, name):
        """Set the name of object.

        :param name: name of the object
        :type name: str
        """
        self._name = name

    def GetName(self):
        """Return the name of the object."""
        return self._name

    def InheritsFrom(self, classname):
        # Dummy function (SensitivityScan does not inherit from any ROOT function)
        return False

    def SetFlatBkgSys(self, value):
        """Define the value of the relative flat systematic uncertainty on the
        background.

        The value is interpreted as the uncertainty relative to the number of background
        events.

        :param value: value of the flat relative background systematic uncertainty
        (default: 0.3)
        :type value: float
        """
        self._flatbkgsys = value

    def GetFlatBkgSys(self):
        """Return the value of the relative flat systematic uncertainty on the
        background.
        """
        return self._flatbkgsys

    def SetIncludeUnderflow(self, boolean):
        """Set whether the underflow bin is included in the calculation.

        :param boolean: True/False
        :type boolean: bool
        """
        self._includeunderflow = boolean

    def GetIncludeUnderflow(self):
        """Check whether the underflow bin is included in the calculation."""
        return self._includeunderflow

    def SetIncludeOverflow(self, boolean):
        """Set whether the overflow bin is included in the calculation.

        :param boolean: True/False
        :type boolean: bool
        """
        self._includeoverflow = boolean

    def GetIncludeOverflow(self):
        """Check whether the overflow bin is included in the calculation."""
        return self._includeoverflow

    def SetYMin(self, value):
        """Set the minimal value of the y-axis.

        :param value: minimal value of the y-axis
        :type value: float
        """
        self._ymin = value

    def GetYMin(self):
        """Return the minimal value of the y-axis."""
        return self._ymin

    def SetYMax(self, value):
        """Set the maximal value of the y-axis.

        :param value: maximal value of the y-axis
        :type value: float
        """
        self._ymax = value

    def GetYMax(self):
        """Return the maximal value of the y-axis."""
        return self._ymax

    def GetSensitivities(self, bn):
        # Returns the sensitivities computed for each signal histogram for the specified
        # bin by taking the cumulative sum of bin contents of signal and background
        # events in the defined direction and using the defined sensitivity measure.
        start = bn if self._direction > 0 else (0 if self._includeunderflow else 1)
        end = (
            bn
            if self._direction < 0
            else (self._nbins + 1 if self._includeoverflow else self._nbins)
        )
        sensitivities = []
        for sighisto in self._sighistos:
            statbkgunc = ROOT.Double(0.0)
            totsig = sighisto.Integral(start, end)
            totbkg = self._bkghisto.IntegralAndError(start, end, statbkgunc)
            totrelbkgunc = ROOT.TMath.Sqrt(
                (statbkgunc / totbkg) ** 2 + self._flatbkgsys ** 2
            )
            try:
                z = self._sensitivitymeasure(totsig, totbkg, totrelbkgunc)
            except ZeroDivisionError:
                logger.warning(
                    "Cannot compute sensitivity for signal histogram '{}' in bin {}! "
                    "Setting to zero...".format(sighisto.GetName(), bn)
                )
                z = 0
            sensitivities.append(z)
        return sensitivities

    def BuildHistos(self):
        # Compute the sensitivities for all signal histograms in the given scan
        # direction and using the given sensitivity measure.
        for bn in range(1, self._nbins + 1, 1):
            sensitivities = self.GetSensitivities(bn)
            for i in range(len(self._sighistos)):
                self._sensitivityhistos[i].SetBinContent(bn, sensitivities[i])

    def SetDrawOption(self, option):
        # Define a drawoption for all sensitivity histograms.
        for scan in self._sensitivityhistos:
            scan.SetDrawOption(option)

    def GetDrawOption(self):
        # Returns the drawoption of the first sensitivity histogram in the list.
        # Corresponds to the drawoption of all other histograms if SetDrawOption was
        # called before.
        return self._sensitivityhistos[0].GetDrawOption()

    def BuildFrame(self, **kwargs):
        # Compute optimal x- and y-axis ranges.
        frame = {}
        for histo in self._sensitivityhistos:
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

    def Draw(self, option=None):
        """Draws all sensitivity histograms to the current pad or canvas."""
        self.SetDrawOption(option)
        suffix = ""
        for scan in self._sensitivityhistos:
            scan.Draw(option + suffix)
            if not option.endswith("SAME"):
                suffix = "SAME"
        self.DrawBenchmarkLines()

    def DrawBenchmarkLines(self):
        currentpad = ROOT.gPad
        if not currentpad:
            return
        xmin = currentpad.GetUxmin()
        xmax = currentpad.GetUxmax()
        ymin = currentpad.GetUymin()
        ymax = currentpad.GetUymax()
        self._benchmarklines = []
        for bm in range(21):
            if bm < ymin:
                continue
            if bm > ymax:
                break
            self._benchmarklines.append(
                Line(xmin, bm, xmax, bm, linestyle=7, linecoloralpha=(ROOT.kBlack, 0.6))
            )
        for line in self._benchmarklines:
            line.Draw()


if __name__ == "__main__":

    from Plot import Plot

    filename = "../data/ds_data18.root"

    h_bkg = Histo1D("h_bkg", "Background", 20, 0.0, 400.0)
    h_sig1 = Histo1D("h_sig1", "Signal 1", 20, 0.0, 400.0)
    h_sig2 = Histo1D("h_sig2", "Signal 2", 20, 0.0, 400.0)

    h_bkg.Fill(filename, tree="DirectStau", varexp="MET", weight="100.0/MET")
    h_sig1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>600")
    h_sig2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>800")

    h_sig1_props = dict(template="signal", linecolor=ROOT.kRed)
    h_sig2_props = dict(template="signal", linecolor=ROOT.kBlue)

    scan = SensitivityScan([(h_sig1, h_sig1_props), (h_sig2, h_sig2_props)], h_bkg)

    p = Plot(npads=2)
    p.Register(h_bkg, template="background", fillcolor=ROOT.kGray)
    p.Register(h_sig1, **h_sig1_props)
    p.Register(h_sig2, **h_sig2_props)
    p.Register(scan, 1, logy=False, ytitle="Z_{N}-value")
    p.Print("test_sensitivityscan.pdf")
