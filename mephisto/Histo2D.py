#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import numpy as np
import root_numpy as rnp

from uuid import uuid4
from array import array
from scipy import interpolate

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from IOManager import IOManager
from Helpers import DissectProperties, MergeDicts


def ExtendProperties(cls):
    # Add properties to configure the countour lines
    cls._properties += ["contour{}".format(p) for p in cls._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Histo2D(MethodProxy, ROOT.TH2D):

    _ignore_properties = ["name", "xtitle", "ytitle", "ztitle"]

    ROOT.TH2.SetDefaultSumw2(True)

    def __init__(self, name, *args, **kwargs):
        MethodProxy.__init__(self)
        self._varexp = None
        self._cuts = None
        self._weight = None
        self._drawoption = ""
        self._contours = []
        self._contourproperties = {}
        if len(args) == 1:
            if isinstance(args[0], ROOT.TH2D):
                ROOT.TH2D.__init__(self, args[0].Clone(name))
                self.SetDirectory(0)
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
        else:
            super(Histo2D, self).DeclareProperty(property, args)

    def Fill(self, *args, **kwargs):
        self._varexp = kwargs.get("varexp")
        self._cuts = kwargs.get("cuts", [])
        self._weight = kwargs.get("weight", "1")
        if len(args) == 1 and isinstance(args[0], str):
            assert len(self._varexp.split(":")) == 2
            IOManager.FillHistogram(self, args[0], **kwargs)
        else:
            super(Histo2D, self).Fill(*args)

    def SetDrawOption(self, string):
        assert isinstance(string, (str, unicode))
        self._drawoption = string
        super(Histo2D, self).SetDrawOption(string)

    def GetDrawOption(self):
        return self._drawoption

    def BuildFrame(self, **kwargs):
        # TODO: Fix ytitle default value and maybe add ypadding option (->TH2::Rebin)?
        logx = kwargs.pop("logx", False)
        logy = kwargs.pop("logy", False)
        xtitle = kwargs.pop("xtitle", None)
        ytitle = kwargs.pop("ytitle", None)
        if xtitle is None:
            xtitle = self._varexp.split(":")[0] if self._varexp is not None else ""
        if ytitle is None:
            ytitle = self._varexp.split(":")[1] if self._varexp is not None else ""
        frame = {
            "xmin": self._xlowbinedges[0],
            "xmax": self._xlowbinedges[self._nbinsx],
            "ymin": self._ylowbinedges[0],
            "ymax": self._ylowbinedges[self._nbinsy],
            "xtitle": xtitle,
            "ytitle": ytitle,
        }
        if logx:
            raise NotImplementedError
        if logy:
            raise NotImplementedError
        return frame

    def Draw(self, drawoption=None):
        hash = uuid4().hex[:8]
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        self.DrawCopy(self.GetDrawOption(), "_{}".format(hash))
        if self._contours:
            super(Histo2D, self).SetContour(
                len(self._contours), array("d", self._contours)
            )
            with UsingProperties(self, **self._contourproperties):
                self.DrawCopy(
                    self.GetDrawOption() + "SAME", "_{}_contours".format(hash)
                )

    def Print(self, path, **kwargs):
        kwargs.setdefault("logy", False)  # overwriting Pad template's default value!
        properties = DissectProperties(kwargs, [Histo2D, Plot, Canvas, Pad])
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Histo2D"], properties["Pad"]))
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def Interpolate(self, *args, **kwargs):
        """Replace zero valued data points by nterpolating between all non-zero data
        point of the grid (if no arguments are given, else see TH2::Interpolate).

        :Keyword Arguments:
        :param method: method of interpolation (default: cubic):
          * nearest: return the value at the data point closest to the point of
            interpolation
          * linear: tessellate the input point set to n-dimensional simplices, and
            interpolate linearly on each simplex
          * cubic: return the value determined from a piecewise cubic, continuously
            differentiable and approximately curvature-minimizing polynomial surface
        :type method: str
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
        for contour in args:
            self._contours.append(contour)

    def GetContour(self):
        return self._contours


if __name__ == "__main__":

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

    h1.Print(
        "test_histo2d_1.png",
        xtitle="X",
        ytitle="Y",
        xunits="k#AA",
        yunits="#mub^{-2}",
        rightmargin=0.15,
        contour=[0.2, 0.5, 0.6],
    )

    h2 = Histo2D("test2", "test2", 40, 0, 400, 40, 0, 400)
    h2.Fill(
        "../data/ds_data18.root",
        tree="DirectStau",
        varexp="tau1Pt:tau2Pt",
        cuts="MET>100",
    )
    h2.Print("test_histo2d_2.png", rightmargin=0.15)
