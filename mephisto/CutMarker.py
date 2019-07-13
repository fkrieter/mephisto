#!/usr/bin/env python2.7

import ROOT

from Line import Line
from Arrow import Arrow
from MethodProxy import *
from Helpers import DissectProperties

from uuid import uuid4


@PreloadProperties
class CutMarker(MethodProxy):
    def __init__(self, cutvalue, **kwargs):
        MethodProxy.__init__(self)
        self._name = "CutMarker_{}".format(uuid4().hex[:8])
        self._cutvalue = cutvalue
        self._lineymin = None
        self._lineymax = None
        self._rellinelength = 0.8
        self._drawarrow = True
        self._relarrowpos = 1.0
        self._relarrowlength = 0.15
        self._direction = 1
        self._drawoption = ""
        self._propcache = DissectProperties(kwargs, [self, Line, Arrow])
        props = self._propcache.pop("CutMarker", {})
        props.setdefault("template", "common")
        self.DeclareProperties(**props)

    def DeclareProperty(self, property, args):
        isvalid = False
        property = property.lower()
        if property in self._properties:
            super(CutMarker, self).DeclareProperty(property, args)
            isvalid = True
        else:
            if property in Line._properties:
                self._propcache["Line"][property] = args
                isvalid = True
            if property in Arrow._properties:
                self._propcache["Arrow"][property] = args
                isvalid = True
        if not isvalid:
            raise KeyError(
                "'{}' object has no property named '{}'!".format(
                    self.__class__.__name__, property
                )
            )

    @classmethod
    def InheritsFrom(cls, classname):
        return False

    def SetName(self, name):
        self._name = name

    def GetName(self):
        return self._name

    def SetDrawOption(self, option):
        self._drawoption = option

    def GetDrawOption(self):
        return self._drawoption

    def SetRelLineLength(self, scale):
        self._rellinelength = scale

    def GetRelLineLength(self):
        return self._rellinelength

    def SetLineYMin(self, ymin):
        self._lineymin = ymin

    def GetLineYMin(self):
        return self._lineymin

    def SetLineYMax(self, ymax):
        self._lineymax = ymax

    def GetLineYMax(self):
        return self._lineymax

    def SetRelArrowLength(self, scale):
        self._relarrowlength = scale

    def GetRelArrowLength(self):
        return self._relarrowlength

    def SetDrawArrow(self, boolean):
        self._drawarrow = boolean

    def GetDrawArrow(self):
        return self._drawarrow

    def SetDirection(self, sign):
        assert sign in ["+", "-"]
        self._direction = {"+": 1, "-": -1}.get(sign)

    def GetDirection(self):
        return {1: "+", -1: "-"}.get(self._direction)

    def Draw(self, option):
        # TODO: Add support for horizontal cut markers, i.e. cuts in y-axis values.
        if option is not None:
            self.SetDrawOption(option)
        currentpad = ROOT.gPad
        frame = currentpad.GetFrame()
        logx = currentpad.GetLogx()
        logy = currentpad.GetLogy()
        padxmin = currentpad.PadtoX(frame.GetX1())
        padxmax = currentpad.PadtoX(frame.GetX2())
        padymin = currentpad.PadtoY(frame.GetY1())
        padymax = currentpad.PadtoY(frame.GetY2())
        lineymin = padymin if self._lineymin is None else self._lineymin
        if logy:
            lineymax = self._rellinelength * padymax
            lineymax = 10 ** (
                self._rellinelength * ROOT.TMath.Log10(padymax / padymin)
                + ROOT.TMath.Log10(padymin)
            )
            arrowpos = 10 ** (
                self._relarrowpos * ROOT.TMath.Log10(lineymax / lineymin)
                + ROOT.TMath.Log10(lineymin)
            )
        else:
            lineymax = (
                (padymax - padymin) * self._rellinelength
                if self._lineymax is None
                else self._lineymax
            )
            arrowpos = (lineymax - lineymin) * self._relarrowpos
        self._line = Line(
            self._cutvalue,
            lineymin,
            self._cutvalue,
            lineymax,
            **self._propcache.get("Line", {})
        )
        self._line.Draw(self.GetDrawOption())
        if self._drawarrow:
            if logx:
                arrowlength = 10 ** (
                    self._relarrowlength * ROOT.TMath.Log10(padymax / padymin)
                    + ROOT.TMath.Log10(padymin)
                )
            else:
                arrowlength = (padxmax - padxmin) * self._relarrowlength
            self._arrow = Arrow(
                self._cutvalue,
                arrowpos,
                self._cutvalue + self._direction * arrowlength,
                arrowpos,
                **self._propcache.get("Arrow", {})
            )
            self._arrow.Draw()
