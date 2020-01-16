#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4
from array import array
from collections import defaultdict

from Pad import Pad
from Plot import Plot
from MethodProxy import *
from Canvas import Canvas
from IOManager import IOManager
from Helpers import DissectProperties, MergeDicts, CheckPath, roundsig


def ExtendProperties(cls):
    # Add properties to configure the _errorband member histogram of Histo1Ds.
    cls._properties += ["errorband{}".format(p) for p in cls._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Histo1D(MethodProxy, ROOT.TH1D):
    r"""Class for 1-dimensional histograms.

    +-------------------------------------------------------------------------------+
    | Inherits from :class:`ROOT.TH1D`, see                                         |
    | official `documentation <https://root.cern.ch/doc/master/classTH1.html>`_     |
    | as well!                                                                      |
    +-------------------------------------------------------------------------------+

    By default :func:`ROOT.TH1.SumW2` is called upon initialization. The properties of
    the **errorband** (which is itself of type ``Histo1D``) of the histogram object can
    be accessed by prepending the prefix 'errorband' in front of the property name. By
    default the errorband's fillcolor and markercolor matches the histogram's linecolor.

    In order to avoid memory leaks, **name** is an inaccessible property despite having
    corresponding getter and setter methods. Furthermore the properties **xtitle**,
    **ytitle** and **ztitle** are defined to be exclusive to the :class:`.Pad` class.
    """

    _ignore_properties = ["name", "xtitle", "ytitle", "ztitle"]

    ROOT.TH1.SetDefaultSumw2(True)

    def __init__(self, name, *args, **kwargs):
        r"""Initialize a 1-dimensional histograms.

        Create an instance of :class:`.Histo1D` with the specified **name** and binning
        (either with uniform or vairable bin widths). Can also be used to copy another
        histogram (or upgrade from a :class:`ROOT.TH1`).

        :param name: name of the histogram
        :type name: ``str``

        :param \*args: see below

        :param \**kwargs: :class:`.Histo1D` properties

        :Arguments:
            Depending on the number of arguments (besides **name**) there are three ways
            to initialize a :class:`.Histo1D` object\:

            * *one* argument\:

                #. **histo** (``Histo1D``, ``TH1``) -- histogram to be copied

            * *two* arguments\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **xlowbinedges** (``list``, ``tuple``) -- list of lower bin-edges on
                   the x-axis (for a histogram with variable bin widths)

            * *four* arguments\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **nbinsx** (``int``) -- number of bins on the x-axis (for a histogram
                   with equal widths)

                #. **xmin** (``float``) -- minimum x-axis value (lower bin-edge of first
                   bin)

                #. **xmax** (``float``) -- maximal x-axis value (upper bin-edge of last
                   bin)
        """
        MethodProxy.__init__(self)
        self._varexp = None
        self._cuts = None
        self._weight = None
        self._errorband = None
        self._drawoption = ""
        self._drawerrorband = False
        self._addtolegend = True
        self._legenddrawoption = ""
        self._stack = False  # Stack property!
        self._attalpha = defaultdict(lambda: 1.0)
        if len(args) == 1:
            if args[0].InheritsFrom("TH1"):
                ROOT.TH1D.__init__(self)
                args[0].Copy(self)
                self.SetDirectory(0)
                self.SetName(name)
            if isinstance(args[0], Histo1D):
                self._varexp = args[0]._varexp
                self._cuts = args[0]._cuts
                self._weight = args[0]._cuts
                self._stack = args[0]._stack
                if args[0]._errorband is not None:
                    self._errorband = Histo1D(
                        "{}_errorband".format(name), args[0]._errorband
                    )
                if not name.endswith("_errorband"):
                    self.DeclareProperties(**args[0].GetProperties())
                    self.DeclareProperties(
                        **args[0]._errorband.GetProperties(prefix="errorband")
                    )
        elif len(args) == 2:
            assert isinstance(args[0], str)
            assert isinstance(args[1], (list, tuple))
            lowbinedges = array("d", args[1])
            ROOT.TH1D.__init__(self, name, args[0], len(lowbinedges) - 1, lowbinedges)
        elif len(args) == 4:
            assert isinstance(args[0], str)
            assert isinstance(args[1], int)
            ROOT.TH1D.__init__(self, name, *args)
        else:
            raise TypeError
        if not name.endswith("_errorband") and self._errorband is None:
            self._errorband = Histo1D("{}_errorband".format(self.GetName()), self)
            for key, value in self.GetTemplate(
                kwargs.get("template", "common")
            ).items():
                kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)
        self._lowbinedges = IOManager._getBinning(self)["xbinning"]
        self._nbins = len(self._lowbinedges) - 1

    def DeclareProperty(self, property, args):
        # Properties starting with "errorband" will be applied to self._errorband.
        # All errorband's properties will be applied after the main histo properties.
        # By default the errorband fillcolor and markercolor matches the histogram's
        # linecolor.
        property = property.lower()
        if property.startswith("errorband"):
            super(Histo1D, self._errorband).DeclareProperty(property[9:], args)
        else:
            super(Histo1D, self).DeclareProperty(property, args)
            if property == "linecolor":
                errbndcol = args
            elif property == "linecoloralpha":
                errbndcol = args[0]
            else:
                return
            super(Histo1D, self._errorband).DeclareProperty("fillcolor", errbndcol)
            super(Histo1D, self._errorband).DeclareProperty("markercolor", errbndcol)

    def Fill(self, *args, **kwargs):
        r"""Fill the histogram with entries.

        If a path (``str``) to an **infile** is given as the only argument the histogram
        if filled using the events in there as specified by the keyword arguments.
        Otherwise the standard :func:`ROOT.TH1.Fill` functionality is used.

        :param \*args: see below

        :param \**kwargs: see below

        :Arguments:
            Depending on the number of arguments (besides **name**) there are three ways
            to initialize a :class:`.Histo1D` object\:

            * *one* argument of type ``str``\:

                #. **infile** (``str``) -- path to the input :py:mod:`ROOT` file (use
                   keyword arguments to define which events to select)

            * otherwise\:

                see :py:mod:`ROOT` documentation of :func:`TH1.Fill` (keyword arguments
                will be ignored)

        :Keyword Arguments:

            * **tree** (``str``) -- name of the input tree

            * **varexp** (``str``) -- name of the branch to be plotted on the x-axis

            * **cuts** (``str``, ``list``, ``tuple``) -- string or list of strings of
              boolean expressions, the latter will default to a logical *AND* of all
              items (default: '1')

            * **weight** (``str``) -- number or branch name to be applied as a weight
              (default: '1')

            * **append** (``bool``) -- append entries to the histogram instead of
              overwriting it (default: ``False``)
        """
        self._varexp = kwargs.get("varexp")
        self._cuts = kwargs.get("cuts", [])
        self._weight = kwargs.get("weight", "1")
        if len(args) == 1 and isinstance(args[0], str):
            IOManager.FillHistogram(self, args[0], **kwargs)
            if not kwargs.get("append", False):
                self._errorband.Reset()
            self._errorband.Add(self)
        else:
            super(Histo1D, self).Fill(*args)

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        r"""Print the histogram to a file.

        Creates a PDF/PNG/... file with the absolute path defined by **path**. If a file
        with the same name already exists it will be overwritten (can be changed  with
        the **overwrite** keyword argument). If **mkdir** is set to ``True`` (default:
        ``False``) directories in **path** with do not yet exist will be created
        automatically. The styling of the histogram, pad and canvas can be configured
        via their respective properties passed as keyword arguments.

        :param path: path of the output file (must end with '.pdf', '.png', ...)
        :type path: ``str``

        :param \**kwargs:
            :class:`.Histo1D`, :class:`.Plot`, :class:`.Canvas` and :class:`.Pad`
            properties + additional properties (see below)

        Keyword Arguments:

            * **inject** (``list``, ``tuple``, ``ROOT.TObject``) -- inject a (list of)
              *drawable* :class:`ROOT` object(s) to the main pad, object properties can
              be specified by passing instead a ``tuple`` of the format
              :code:`(obj, props)` where :code:`props` is a ``dict`` holding the object
              properties (default: \[\])

            * **overwrite** (``bool``) -- overwrite an existing file located at **path**
              (default: ``True``)

            * **mkdir** (``bool``) -- create non-existing directories in **path**
              (default: ``False``)
        """
        injections = {"inject0": kwargs.pop("inject", [])}
        properties = DissectProperties(kwargs, [Histo1D, Plot, Canvas, Pad])
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Histo1D"], properties["Pad"]))
        plot.Print(
            path, **MergeDicts(properties["Plot"], properties["Canvas"], injections)
        )

    def SetDrawOption(self, option):
        r"""Define the draw option for the histogram.

        :param option: draw option (see :class:`ROOT.THistPainter`
            `class reference <https://root.cern/doc/master/classTHistPainter.html>`_)
        :type option: ``str``
        """
        if not isinstance(option, (str, unicode)):
            raise TypeError
        self._drawoption = option
        super(Histo1D, self).SetDrawOption(option)

    def GetDrawOption(self):
        r"""Return the draw option defined for the histogram.

        :returntype: ``str``
        """
        return self._drawoption

    def SetDrawErrorband(self, boolean):
        r"""Define whether the errorband should be drawn for the histogram.

        :param boolean: if set to ``True`` the errorband will be drawn
        :type boolean: ``bool``
        """
        self._drawerrorband = boolean

    def GetDrawErrorband(self):
        r"""Return whether the errorband should be drawn for the histogram.

        :returntype: ``bool``
        """
        return self._drawerrorband

    def GetXTitle(self):
        r"""Return the histogram's x-axis title.

        :returntype: ``str``
        """
        return self.GetXaxis().GetTitle()

    def GetYTitle(self):
        r"""Return the histogram's y-axis title.

        :returntype: ``str``
        """
        return self.GetYaxis().GetTitle()

    def Draw(self, option=None):
        # Draw the histogram to the current TPad together with it's errorband.
        if option is not None:
            self.SetDrawOption(option)
        self.DrawCopy(self.GetDrawOption(), "_{}".format(uuid4().hex[:8]))
        if self._drawerrorband:
            self._errorband.Reset()
            self._errorband.Add(self)  # making sure the erroband is up-to-date
            self._errorband.DrawCopy(
                self._errorband.GetDrawOption() + "SAME", "_{}".format(uuid4().hex[:8])
            )

    def GetBinWidths(self):
        r"""Return a list of all bin widths.

        :returntype: ``list``
        """
        binwidths = [
            self._lowbinedges[i + 1] - self._lowbinedges[i]
            for i in range(len(self._lowbinedges) - 1)
        ]
        return binwidths

    def BuildFrame(self, **kwargs):
        # Return the optimal axis ranges for the histogram. Gets called by Plot when the
        # histogram is registered to it.
        scale = 1.0 + kwargs.get("ypadding", 0.25)  # Pad property
        logx = kwargs.get("logx", False)
        logy = kwargs.get("logy", False)
        xtitle = kwargs.get("xtitle", None)
        ytitle = kwargs.get("ytitle", "Entries")
        xunits = kwargs.get("xunits", None)
        if xtitle is None:
            xtitle = self._varexp if self._varexp is not None else ""
        binwidths = [roundsig(w, 4, decimals=True) for w in self.GetBinWidths()]
        if len(set(binwidths)) == 1:
            binwidth = (
                int(binwidths[0])
                if binwidths[0].is_integer()
                else round(binwidths[0], 1)
            )
            if (
                not ytitle.endswith((str(binwidth), str(xunits)))
                and self.GetNbinsX() > 1
            ):
                ytitle += " / {}".format(binwidth)
            if xunits and not ytitle.endswith(xunits):
                ytitle += " {}".format(xunits)
        maxbinval = self.GetMaximum()
        frame = {
            "xmin": self._lowbinedges[0],
            "xmax": self._lowbinedges[self._nbins],
            "ymin": 0.0,
            "ymax": maxbinval if maxbinval > 0 else 1.1e-2,
            "xtitle": xtitle,
            "ytitle": ytitle,
        }
        if logx:
            frame["xmin"] = kwargs.get("xmin", 1e-2)
        if logy:
            frame["ymin"] = kwargs.get("ymin", 1e-2)
            frame["ymax"] = 10 ** (
                scale * ROOT.TMath.Log10(frame["ymax"] / frame["ymin"])
                + ROOT.TMath.Log10(frame["ymin"])
            )
        else:
            frame["ymax"] *= scale
        return frame

    def Add(self, histo, scale=1):
        r"""Add another **histo** to the current histogram.

        A global weight can be set for the **histo** via the **scale**. The raw
        (unweighted) entries of the histograms will be added.

        :param histo: histogram to be added to the current object
        :type histo: ``Histo1D``, ``TH1D``

        :param scale: global weight multiplied to **histo** (default: 1)
        :param scale: ``float``
        """
        raw_entries = self.GetEntries() + histo.GetEntries()
        super(Histo1D, self).Add(histo, scale)
        self.SetEntries(raw_entries)

    def SetLegendDrawOption(self, option):
        r"""Define the draw option for the histogram's legend.

        :param option: draw option (see :class:`ROOT.TLegend`
            `class reference <https://root.cern/doc/master/classTLegend.html>`_)
        :type option: ``str``
        """
        self._legenddrawoption = option

    def GetLegendDrawOption(self):
        r"""Return the draw option defined for the histogram's legend.

        :returntype: ``str``
        """
        return self._legenddrawoption

    def SetLineAlpha(self, alpha):
        r"""Define the transparency of the histogram's line attribute.

        :param option: transparency of the histogram's line attribute
            (:math:`\alpha \in [0,1]` )
        :type option: ``float``
        """
        self._attalpha["line"] = alpha
        self.SetLineColorAlpha(self.GetLineColor(), alpha)

    def GetLineAlpha(self):
        r"""Return tthe transparency of the histogram's line attribute.

        :returntype: ``float``
        """
        return self._attalpha["line"]

    def SetFillAlpha(self, alpha):
        r"""Define the transparency of the histogram's fill attribute.

        :param option: transparency of the histogram's fill attribute
            (:math:`\alpha \in [0,1]` )
        :type option: ``float``
        """
        self._attalpha["fill"] = alpha
        self.SetFillColorAlpha(self.GetFillColor(), alpha)

    def GetFillAlpha(self):
        r"""Return tthe transparency of the histogram's fill attribute.

        :returntype: ``float``
        """
        return self._attalpha["fill"]

    def SetMarkerAlpha(self, alpha):
        r"""Define the transparency of the histogram's marker attribute.

        :param option: transparency of the histogram's marker attribute
            (:math:`\alpha \in [0,1]` )
        :type option: ``float``
        """
        self._attalpha["marker"] = alpha
        self.SetMarkerColorAlpha(self.GetMarkerColor(), alpha)

    def GetMarkerAlpha(self):
        r"""Return tthe transparency of the histogram's marker attribute.

        :returntype: ``float``
        """
        return self._attalpha["marker"]

    def SetLineColor(self, color):
        self.SetLineColorAlpha(color, self._attalpha["line"])

    def SetFillColor(self, color):
        self.SetFillColorAlpha(color, self._attalpha["fill"])

    def SetMarkerColor(self, color):
        self.SetMarkerColorAlpha(color, self._attalpha["marker"])

    def SetAddToLegend(self, boolean):
        r"""Define whether the histogram should be added to the :class:`.Legend`.

        :param boolean: if set to ``True`` the histogram will be added to the
            :class:`.Legend`
        :type boolean: ``bool``
        """
        self._addtolegend = boolean

    def GetAddToLegend(self):
        r"""Return whether the histogram should be added to the :class:`.Legend`.

        :returntype: ``bool``
        """
        return self._addtolegend

    def SetStack(self, boolean):
        """Set how the object is displayed if added to a :class:`.Stack`.

        If set to ``True`` and the histogram is registered to a :class:`.Stack`, it will
        be displayed in the stack of histograms.

        :param boolean: if set to ``True`` the histogram will be displayed in the stack
            of histograms
        :type boolean: ``bool``
        """
        self._stack = boolean

    def GetStack(self):
        r"""Return how the object is displayed if added to a :class:`.Stack`.

        :returntype: ``bool``
        """
        return self._stack


def main():

    filename = "../data/ds_data18.root"
    h = Histo1D("test", "test", 20, 0.0, 400.0)
    # Histo1D.PrintAvailableProperties()
    h.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    # print(h)
    # print(h.Integral())
    h.Print("test_histo_data.pdf", template="data", logy=False, xunits="GeV")
    h.Print(
        "test_histo_background.pdf", template="background", logy=False, xunits="GeV"
    )
    h2 = Histo1D("test2", h, template="signal", drawerrorband=True)
    h3 = Histo1D("test3", h2, linecolor=ROOT.kGreen)
    h3.Print("test_histo_signal.pdf", logy=True, xunits="GeV")


if __name__ == "__main__":
    main()
