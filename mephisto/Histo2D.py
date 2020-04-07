#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import numpy as np
import root_numpy as rnp

from uuid import uuid4
from array import array
from scipy import interpolate
from collections import defaultdict

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from IOManager import IOManager
from Helpers import DissectProperties, MergeDicts, CheckPath


def ExtendProperties(cls):
    # Add properties to configure the countour lines. Define proxies for z-axis
    # properties.
    cls._properties += ["contour{}".format(p) for p in cls._properties]  # append!
    cls._zaxisproxies = {}
    for prop in [
        "Title",
        "TitleFont",
        "TitleSize",
        "TitleColor",
        "TitleOffset",
        "LabelFont",
        "LabelSize",
        "LabelColor",
        "LabelOffset",
    ]:
        setter = "Set{}".format(prop)
        cls._zaxisproxies[
            "z{}".format(prop.lower())
        ] = lambda z, v, bound_setter=setter: getattr(z, bound_setter)(v)
    cls._properties += cls._zaxisproxies.keys()
    return cls


@ExtendProperties
@PreloadProperties
class Histo2D(MethodProxy, ROOT.TH2D):
    r"""Class for 2-dimensional histograms.

    +-------------------------------------------------------------------------------+
    | Inherits from :class:`ROOT.TH2D`, see                                         |
    | official `documentation <https://root.cern.ch/doc/master/classTH1.html>`_     |
    | as well!                                                                      |
    +-------------------------------------------------------------------------------+

    By default :func:`ROOT.TH2.SumW2` is called upon initialization. The properties of
    the **contour** (which is itself of type ``Histo2D``) of the histogram object can be
    accessed by prepending the prefix 'contour' in front of the property name.

    In order to avoid memory leaks, **name** is an inaccessible property despite having
    corresponding getter and setter methods. Furthermore the properties **xtitle**,
    **ytitle** are defined to be exclusive to the :class:`.Pad` class. However, the
    title and other properties of the z-axis (automatically created if the specified
    drawoption contains ``Z``) are tied to the ``Histo2D`` class.
    """

    _ignore_properties = [
        "at",
        "bincontent",
        "binerror",
        "bins",
        "canextend",
        "cellcontent",
        "cellerror",
        "content",
        "entries",
        "error",
        "maximum",
        "minimum",
        "name",
        "nametitle",
        "statoverflows",
        "stats",
        "xtitle",
        "ytitle",
        "ztitle",
    ]

    ROOT.TH2.SetDefaultSumw2(True)

    def __init__(self, name, *args, **kwargs):
        r"""Initialize a 2-dimensional histograms.

        Create an instance of :class:`.Histo2D` with the specified **name** and binning
        (either with uniform or vairable bin widths). Can also be used to copy another
        histogram (or upgrade from a :class:`ROOT.TH2`).

        :param name: name of the histogram
        :type name: ``str``

        :param \*args: see below

        :param \**kwargs: :class:`.Histo2D` properties

        :Arguments:
            Depending on the number of arguments (besides **name**) there are three ways
            to initialize a :class:`.Histo2D` object\:

            * *one* argument\:

                #. **histo** (``Histo2D``, ``TH2``) -- histogram to be copied

            * *three* arguments\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **xlowbinedges** (``list``, ``tuple``) -- list of lower bin-edges on
                   the x-axis (for a histogram with variable bin widths)

                #. **ylowbinedges** (``list``, ``tuple``) -- list of lower bin-edges on
                   the y-axis (for a histogram with variable bin widths)

            * *five* arguments (variable x-axis binning)\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **xlowbinedges** (``list``, ``tuple``) -- list of lower bin-edges on
                   the x-axis (for a histogram with variable bin widths)

                #. **nbinsy** (``int``) -- number of bins on the y-axis (for a histogram
                   with equal widths)

                #. **ymin** (``float``) -- minimum y-axis value (lower bin-edge of first
                   bin)

                #. **ymax** (``float``) -- maximal y-axis value (upper bin-edge of last
                   bin)

            * *five* arguments (variable y-axis binning)\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **nbinsx** (``int``) -- number of bins on the x-axis (for a histogram
                   with equal widths)

                #. **xmin** (``float``) -- minimum x-axis value (lower bin-edge of first
                   bin)

                #. **xmax** (``float``) -- maximal x-axis value (upper bin-edge of last
                   bin)

                #. **ylowbinedges** (``list``, ``tuple``) -- list of lower bin-edges on
                   the y-axis (for a histogram with variable bin widths)

            * *seven* arguments\:

                #. **title** (``str``) -- histogram title that will be used by the
                   :class:`.Legend` class

                #. **nbinsx** (``int``) -- number of bins on the x-axis (for a histogram
                   with equal widths)

                #. **xmin** (``float``) -- minimum x-axis value (lower bin-edge of first
                   bin)

                #. **xmax** (``float``) -- maximal x-axis value (upper bin-edge of last
                   bin)

                #. **nbinsy** (``int``) -- number of bins on the y-axis (for a histogram
                   with equal widths)

                #. **ymin** (``float``) -- minimum y-axis value (lower bin-edge of first
                   bin)

                #. **ymax** (``float``) -- maximal y-axis value (upper bin-edge of last
                   bin)
        """
        MethodProxy.__init__(self)
        self._varexp = None
        self._cuts = None
        self._weight = None
        self._drawoption = ""
        self._palette = 57  # ROOT default
        self._contours = []
        self._contourproperties = {}
        self._zmin = None
        self._zmax = None  # = max. bin content
        self._zaxisproperties = {}
        if len(args) == 1:
            if args[0].InheritsFrom("TH2"):
                ROOT.TH2D.__init__(self)
                args[0].Copy(self)
                self.SetDirectory(0)
                self.SetName(name)
            if isinstance(args[0], Histo2D):
                self._varexp = args[0]._varexp
                self._cuts = args[0]._cuts
                self._weight = args[0]._cuts
                self._contours = args[0]._contours
                self._contourproperties = args[0]._contourproperties
        elif len(args) == 3:
            assert isinstance(args[0], str)
            assert isinstance(args[1], (list, tuple))
            assert isinstance(args[2], (list, tuple))
            xlowbinedges = array("d", args[1])
            ylowbinedges = array("d", args[2])
            ROOT.TH2D.__init__(
                self,
                name,
                args[0],
                len(xlowbinedges) - 1,
                xlowbinedges,
                len(ylowbinedges) - 1,
                ylowbinedges,
            )
        elif len(args) == 5:
            assert isinstance(args[0], str)
            if isinstance(args[1], (list, tuple)):
                assert isinstance(args[2], int)
                xlowbinedges = array("d", args[1])
                ROOT.TH2D.__init__(
                    self, name, args[0], len(xlowbinedges) - 1, xlowbinedges, *args[2:]
                )
            elif isinstance(args[4], (list, tuple)):
                assert isinstance(args[1], int)
                ylowbinedges = array("d", args[4])
                ROOT.TH2D.__init__(
                    self,
                    name,
                    args[0],
                    args[1],
                    args[2],
                    args[3],
                    len(ylowbinedges) - 1,
                    ylowbinedges,
                )
        elif len(args) == 7:
            assert isinstance(args[0], str)
            assert isinstance(args[1], int)
            assert isinstance(args[4], int)
            ROOT.TH2D.__init__(self, name, *args)
        else:
            raise TypeError
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)
        self._xlowbinedges = IOManager._getBinning(self)["xbinning"]
        self._ylowbinedges = IOManager._getBinning(self)["ybinning"]
        self._nbinsx = len(self._xlowbinedges) - 1
        self._nbinsy = len(self._ylowbinedges) - 1

    def DeclareProperty(self, property, args):
        # Properties starting with "contour" will be stored in a dictionary and get
        # applied when the object is drawn.
        property = property.lower()
        if property.startswith("contour") and property != "contour":
            self._contourproperties[property[7:]] = args
        elif property in self._zaxisproxies.keys():
            self._zaxisproperties[property] = args
        else:
            super(Histo2D, self).DeclareProperty(property, args)

    def Fill(self, *args, **kwargs):
        r"""Fill the histogram with entries.

        If a path (``str``) to an **infile** is given as the only argument the histogram
        if filled using the events in there as specified by the keyword arguments.
        Otherwise the standard :func:`ROOT.TH2.Fill` functionality is used.

        :param \*args: see below

        :param \**kwargs: see below

        :Arguments:
            Depending on the number of arguments (besides **name**) there are three ways
            to initialize a :class:`.Histo2D` object\:

            * *one* argument of type ``str``\:

                #. **infile** (``str``) -- path to the input :py:mod:`ROOT` file (use
                   keyword arguments to define which events to select)

            * otherwise\:

                see :py:mod:`ROOT` documentation of :func:`TH1.Fill` (keyword arguments
                will be ignored)

        :Keyword Arguments:

            * **tree** (``str``) -- name of the input tree

            * **varexp** (``str``) -- name of the branch to be plotted on the x-axis and
              y-axis (format 'y:x')

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
            assert len(self._varexp.split(":")) == 2
            IOManager.FillHistogram(self, args[0], **kwargs)
        else:
            super(Histo2D, self).Fill(*args)

    def SetDrawOption(self, option):
        r"""Define the draw option for the histogram.

        :param option: draw option (see :class:`ROOT.THistPainter`
            `class reference <https://root.cern/doc/master/classTHistPainter.html>`_)
        :type option: ``str``
        """
        if not isinstance(option, (str, unicode)):
            raise TypeError
        self._drawoption = option
        super(Histo2D, self).SetDrawOption(option)

    def GetDrawOption(self):
        r"""Return the draw option defined for the histogram.

        :returntype: ``str``
        """
        return self._drawoption

    def SetPalette(self, num):
        r"""Define the color palette ID for the histogram.

        :param num: color palette ID (see :class:`ROOT.TColor`
            `class reference <https://root.cern.ch/doc/master/classTColor.html>`_)
        :type option: ``int``
        """
        self._palette = num
        ROOT.gStyle.SetPalette(self._palette)

    def GetPalette(self):
        r"""Return the color palette ID defined for the histogram.

        :returntype: ``int``
        """
        return self._palette

    def BuildFrame(self, **kwargs):
        # Return the optimal axis ranges for the histogram. Gets called by Plot when the
        # histogram is registered to it.
        logx = kwargs.pop("logx", False)
        logy = kwargs.pop("logy", False)
        logz = kwargs.pop("logz", False)
        xtitle = kwargs.pop("xtitle", None)
        ytitle = kwargs.pop("ytitle", None)
        if xtitle is None:
            xtitle = self._varexp.split(":")[1] if self._varexp is not None else ""
        if ytitle is None or ytitle == "Entries":  # Pad default
            ytitle = self._varexp.split(":")[0] if self._varexp is not None else ""
        frame = {
            "xmin": self._xlowbinedges[0],
            "xmax": self._xlowbinedges[self._nbinsx],
            "ymin": self._ylowbinedges[0],
            "ymax": self._ylowbinedges[self._nbinsy],
            "xtitle": xtitle,
            "ytitle": ytitle,
        }
        return frame

    def SetZMin(self, value):
        self.GetZaxis().SetRangeUser(value, self.GetZMax())
        self._zmin = value

    def GetZMin(self):
        if self._zmin is None:
            self._zmin = self.GetMinimum()
        return self._zmin

    def SetZMax(self, value):
        self.GetZaxis().SetRangeUser(self.GetZMin(), value)
        self._zmax = value

    def GetZMax(self):
        if self._zmax is None:
            self._zmax = self.GetMaximum()
        return self._zmax

    def Draw(self, drawoption=None):
        # Draw the histogram to the current TPad together with it's contours.
        # TODO: Make TPaletteAxis properties configurable (like z-axis properties).
        ROOT.gStyle.SetNumberContours(999)  # smooth color gradient
        hash = uuid4().hex[:8]
        for prop, args in self._zaxisproperties.items():
            self._zaxisproxies[prop](self.GetZaxis(), args)
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        self.DrawCopy(self.GetDrawOption(), "_{}".format(hash))
        # ROOT.gPad.Update()
        # copy = ROOT.gROOT.FindObject("{}_{}".format(self.GetName(), hash))
        # self._palette = copy.GetListOfFunctions().FindObject("palette")
        if self._contours:
            super(Histo2D, self).SetContour(
                len(self._contours), array("d", self._contours)
            )
            with UsingProperties(self, **self._contourproperties):
                self.DrawCopy(
                    self.GetDrawOption() + "SAME", "_{}_contours".format(hash)
                )

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

        :param \**kwargs: :class:`.Histo2D`, :class:`.Plot`, :class:`.Canvas` and
            :class:`.Pad` properties + additional properties (see below)

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
        kwargs.setdefault("logy", False)  # overwriting Pad template's default value!
        properties = DissectProperties(kwargs, [Histo2D, Plot, Canvas, Pad])
        if any(
            map(
                lambda s: "Z" in s.upper(),
                [self.GetDrawOption(), properties["Pad"].get("drawoption", "")],
            )
        ):
            properties["Pad"].setdefault("rightmargin", 0.18)
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Histo2D"], properties["Pad"]))
        plot.Print(
            path, **MergeDicts(properties["Plot"], properties["Canvas"], injections)
        )

    def Interpolate(self, *args, **kwargs):
        r"""Replace zero valued data points by interpolating between all non-zero data
        point of the grid if no arguments are given. Otherwise the standard
        :func:`ROOT.TH2.Interpolate` functionality is used.

        In the former case the :py:mod:`scipy`'s :func:`interpolate.griddata` function
        is used.

        :param \*args: See :py:mod:`ROOT` documentation of :func:`ROOT.TH2.Interpolate`

        :param \**kwargs: see below

        :Keyword Arguments:
            * **method** (``str``) -- method of interpolation (default: 'cubic')

                * **nearest**: return the value at the data point closest to the point
                  of interpolation

                * **linear**: tessellate the input point set to n-dimensional simplices,
                  and interpolate linearly on each simplex

                * **cubic**: return the value determined from a piecewise cubic,
                  continuously differentiable and approximately curvature-minimizing
                  polynomial surface
        """
        if len(args) == 0:
            # https://stackoverflow.com/a/39596856/10986034
            method = kwargs.pop("method", "cubic")
            array = rnp.hist2array(self, include_overflow=True)
            array[array == 0] = np.nan
            x = np.arange(0, array.shape[1])
            y = np.arange(0, array.shape[0])
            array = np.ma.masked_invalid(array)
            xx, yy = np.meshgrid(x, y)
            x1 = xx[~array.mask]
            y1 = yy[~array.mask]
            newarr = array[~array.mask]
            GD1 = interpolate.griddata(
                (x1, y1), newarr.ravel(), (xx, yy), method=method, fill_value=0.0
            )
            rnp.array2hist(GD1, self)
        else:
            super(Histo2D, self).Interpolate(*args)

    def SetContour(self, *args):
        r"""Define the contour levels.

        A contour line will be drawn at values of the histogram equal to the specified
        levels.

        :param \*args: contour levels
        :type \*args: ``float``
        """
        self._contours = list(args)

    def GetContour(self):
        r"""Return a list of all contour levels.

        :returntype: ``list``
        """
        return self._contours

    def RetrieveContourGraphDict(self):
        r"""Return a dictionary with a list of graphs representing the contour lines
        for any given contour level.

        :returntype: ``dict``
        """
        # https://root.cern/doc/master/classTHistPainter.html#HP16a
        if not self._contours:
            return {}
        graphs = defaultdict(lambda: [])
        htmp = Histo2D("{}_{}".format(self.GetName(), uuid4().hex[:8]), self)
        htmp.SetContour(*self._contours)
        canv = ROOT.TCanvas()
        canv.cd()
        super(Histo2D, htmp).Draw("CONT LIST")
        ROOT.gPad.Update()
        del canv, htmp
        conts = ROOT.gROOT.GetListOfSpecials().FindObject("contours")
        for i, contour in enumerate(self._contours):
            contLevel = conts.At(i)
            curv = contLevel.First().Clone()
            graphs[contour].append(curv)
        return graphs


if __name__ == "__main__":

    from Graph import Graph

    nbinsx = 100
    nbinsy = 100

    xsparsity = 4
    ysparsity = 4

    norm = float(nbinsx ** 2 + nbinsy ** 2)

    h1 = Histo2D("test1", "test1", nbinsx, 0, nbinsx, nbinsy, 0, nbinsy)

    for x in range(nbinsx + 1):
        for y in range(nbinsy + 1):
            if x % xsparsity == 0 and y % ysparsity == 0:
                h1.Fill(x, y, ((x + 1) ** 2 + (y + 1) ** 2) / norm)

    h1.Interpolate()  # because TH2::Smooth sucks

    h1.SetContour(0.3)
    graphsdict = h1.RetrieveContourGraphDict()
    for i, (cont, graphs) in enumerate(graphsdict.items()):
        for j, graph in enumerate(graphs):
            g = Graph("mycontour", graph)
            g.Print("test_contour{}_graph{}.pdf".format(i, j))

    h1.Print(
        "test_histo2d_1.png",
        xtitle="X",
        ytitle="Y",
        xunits="k#AA",
        yunits="#mub^{-2}",
        rightmargin=0.15,
        contour=[0.2, 0.5, 0.6],
    )

    h2 = Histo2D("test2", "test2", 45, -50, 400, 35, 50, 400)
    h2.Fill(
        "../data/ds_data18.root",
        tree="DirectStau",
        varexp="tau1Pt:tau2Pt",
        cuts="MET>100",
    )
    h2.Print(
        "test_histo2d_2.png",
        # rightmargin=0.18,
        ztitleoffset=1.2,
        ztitle="meep",
        # zmin=10.0,
    )
