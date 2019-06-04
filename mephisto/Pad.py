#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import re

from MethodProxy import *
from Helpers import DissectProperties


def ExtendMethods(cls):
    # Add dedicated methods (+ their associated properties) for each axis of the frame.
    # The axis name is added to the beginning of the property name, e.g. 'xlabelfont'
    # will configure the labelfont of the pad frame's x-axis only, while 'labelfont'
    # will do so for all axes (see setter method below).
    # (See: https://www.reddit.com/r/learnpython/comments/50yk7s/)
    cls._frameproperties = []
    for prop in [
        "BinLabels",
        "LabelFont",
        "LabelSize",
        "LabelColor",
        "LabelOffset",
        "LabelOption",
        "TitleFont",
        "TitleSize",
        "TitleColor",
        "TitleOffset",
        "Ndivisions",
    ]:
        cls._frameproperties.append(prop.lower())
        for coord in "xyz":
            cls._frameproperties.append("{}{}".format(coord, prop.lower()))
            setattr(
                cls,
                "Set{}{}".format(coord.upper(), prop),
                lambda cls, v, bound_coord=coord, bound_prop=prop: getattr(
                    cls, "Set{}".format(bound_prop)
                )(v, axes=bound_coord),
            )
            coordprop = "{}{}".format(coord.upper(), prop)
            if coordprop.lower() in cls._properties:
                continue
            cls._properties.append(coordprop.lower())
            cls._methods.append("Set{}".format(coordprop))
    return cls


@ExtendMethods
@PreloadProperties
class Pad(MethodProxy, ROOT.TPad):
    def __init__(self, name="undefined", *args, **kwargs):
        MethodProxy.__init__(self)
        self._frame = None
        self._drawframe = False
        self._xmin = self._ymin = 1e-2
        self._xmax = self._ymax = 1.0
        self._xunits, self._yunits = None, None
        self._ypadding = 0.25  # frame is 25% higher than max. bin content
        self._drawlegend = False
        self._legendxshift = 0.0
        self._legendyshift = 0.0
        self._labeloption = {}
        if len(args) > 0:
            self._xposlow, self._yposlow = args[0:2]
            self._xposup, self._yposup = args[2:4]
            ROOT.TPad.__init__(self, name, "", *args)
        else:
            self._xposlow, self._yposlow, self._xposup, self._yposup = (
                0.0,
                0.0,
                1.0,
                1.0,
            )
            ROOT.TPad.__init__(self)
            self.SetName(name)
        self.SetTitle(";;")
        properties = DissectProperties(kwargs, [{"Frame": self._frameproperties}, Pad])
        self.Draw()
        self.DeclareProperty("padposition", properties["Pad"].pop("padposition"))
        self.DeclareProperties(**properties["Pad"])
        self.Draw()
        self.cd()
        if self._drawframe:
            self.DrawFrame(**properties["Frame"])

    def SetPadPosition(self, xlow, ylow, xup, yup):
        self._xposlow, self._yposlow = xlow, ylow
        self._xposup, self._yposup = xup, yup
        self.SetPad(xlow, ylow, xup, yup)

    def GetPadPosition(self):
        return (self._xposlow, self._yposlow, self._xposup, self._yposup)

    def GetPadWidth(self):
        return self._xposup - self._xposlow

    def GetPadHeight(self):
        return self._yposup - self._yposlow

    def GetXMin(self):
        return self._xmin

    def GetXMax(self):
        return self._xmax

    def GetYMin(self):
        return self._ymin

    def GetYMax(self):
        return self._ymax

    def SetXMin(self, xmin):
        if self.GetLogx() and xmin <= 0:
            logger.error("Cannot set 'xmin' to {} on log-axis!".format(xmin))
            raise ValueError
        self._xmin = xmin

    def SetXMax(self, xmax):
        if self.GetLogx() and xmax <= 0:
            logger.error("Cannot set 'xmax' to {} on log-axis!".format(xmax))
            raise ValueError
        self._xmax = xmax

    def SetYMin(self, ymin):
        if self.GetLogy() and ymin <= 0:
            logger.error("Cannot set 'ymin' to {} on log-axis!".format(ymin))
            raise ValueError
        self._ymin = ymin

    def SetYMax(self, ymax):
        if self.GetLogy() and ymax <= 0:
            logger.error("Cannot set 'ymax' to {} on log-axis!".format(ymax))
            raise ValueError
        self._ymax = ymax

    def SetLogx(self, boolean):
        if boolean and self.GetXMin() * self.GetXMax() <= 0:
            logger.error(
                "Cannot set 'logx' to '{}' on axis with negative"
                " values!".format(boolean)
            )
            raise ValueError
        super(Pad, self).SetLogx(boolean)

    def SetLogy(self, boolean):
        if boolean and self.GetYMin() * self.GetYMax() <= 0:
            logger.error(
                "Cannot set 'logy' to '{}' on axis with negative"
                " values!".format(boolean)
            )
            raise ValueError
        super(Pad, self).SetLogy(boolean)

    def SetXTitle(self, xtitle):
        ytitle = self.GetTitle().split(";")[2]
        prev_xtitle = self.GetTitle().split(";")[1]
        xunits = re.search("\[(.*?)\]$", prev_xtitle)
        if xunits:
            xtitle += " {}".format(xunits.group())
        self.SetTitle(";{};{}".format(xtitle, ytitle))

    def GetXTitle(self):
        return self.GetTitle().split(";")[1]

    def SetYTitle(self, ytitle):
        xtitle = self.GetTitle().split(";")[1]
        prev_ytitle = self.GetTitle().split(";")[2]
        yunits = re.search("\[(.*?)\]$", prev_ytitle)
        if yunits:
            ytitle += " {}".format(yunits.group())
        self.SetTitle(";{};{}".format(xtitle, ytitle))

    def GetYTitle(self):
        return self.GetTitle().split(";")[2]

    def SetXUnits(self, xunits):
        assert isinstance(xunits, str)
        self._xunits = xunits
        xtitle = self.GetXTitle()
        if re.search("\[(.*?)\]$", xtitle):
            re.sub("\[(.*?)\]$", "[{}]".format(self._xunits), xtitle)
        else:
            xtitle += " [{}]".format(self._xunits)
        self.SetXTitle(xtitle)

    def GetXUnits(self):
        return self._xunits

    def SetYUnits(self, yunits):
        assert isinstance(yunits, str)
        self._yunits = yunits
        ytitle = self.GetYTitle()
        if re.search("\[(.*?)\]$", ytitle):
            re.sub("\[(.*?)\]$", "[{}]".format(self._yunits), ytitle)
        else:
            ytitle += " [{}]".format(self._yunits)
        self.SetYTitle(ytitle)

    def GetYUnits(self):
        return self._yunits

    def SetFrame(self, xmin, ymin, xmax, ymax):
        self._xmin = xmin
        self._ymin = ymin
        self._xmax = xmax
        self._ymax = ymax

    def GetFrame(self):
        return (self._xmin, self._ymin, self._xmax, self._ymax)

    def SetDrawFrame(self, boolean):
        self._drawframe = boolean

    def GetDrawFrame(self):
        return self._drawframe

    def DrawFrame(self, *args, **kwargs):
        if len(args) == 4:
            for i, prop in enumerate(["xmin", "ymin", "xmax", "ymax"]):
                self.DeclareProperty(prop, args[i])
        elif len(args) != 0:
            logger.error(
                "DrawFrame() takes exactly 0 or 4 arguments"
                " ({} given)".format(len(args))
            )
            raise TypeError
        assert self._xmin < self._xmax
        assert self._ymin < self._ymax
        self._frame = super(Pad, self).DrawFrame(
            self._xmin, self._ymin, self._xmax, self._ymax, self.GetTitle()
        )
        self.DeclareProperties(**kwargs)

    def SetLabelColor(self, color, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetLabelColor(color)

    def SetLabelFont(self, font, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetLabelFont(font)

    def SetLabelSize(self, size, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetLabelSize(size)

    def SetLabelOffset(self, offset, axes="xyz"):
        canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            scale = 700.0 / canvaswidth
            axis.SetLabelOffset(offset * scale)

    def SetTitleColor(self, color, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetTitleColor(color)

    def SetTitleFont(self, font, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetTitleFont(font)

    def SetTitleSize(self, size, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetTitleSize(size)

    def SetTitleOffset(self, offset, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            canvasheight = self.GetCanvas().GetWh() * self.GetCanvas().GetAbsHNDC()
            canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
            padheight = self.GetWh() * self.GetAbsHNDC()
            padwidth = self.GetWw() * self.GetAbsWNDC()
            scale = {
                "x": (canvasheight / canvaswidth) * (padwidth / padheight),
                "y": (canvasheight / canvaswidth),
            }.get(coord.lower(), 1.0)
            axis.SetTitleOffset(offset * scale)

    def SetNdivisions(self, ndiv, optim=True, axes="xyz"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            axis.SetNdivisions(ndiv, optim)

    def SetTopMargin(self, margin):
        canvasheight = self.GetCanvas().GetWh() * self.GetCanvas().GetAbsHNDC()
        canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
        padheight = self.GetWh() * self.GetAbsHNDC()
        scale = canvaswidth / canvasheight
        scale *= canvasheight / padheight
        scale *= 700.0 / canvaswidth
        super(Pad, self).SetTopMargin(margin * scale)

    def SetBottomMargin(self, margin):
        canvasheight = self.GetCanvas().GetWh() * self.GetCanvas().GetAbsHNDC()
        canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
        padheight = self.GetWh() * self.GetAbsHNDC()
        scale = canvaswidth / canvasheight
        scale *= canvasheight / padheight
        scale *= 700.0 / canvaswidth
        super(Pad, self).SetBottomMargin(margin * scale)

    def SetLeftMargin(self, margin):
        canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
        scale = 700.0 / canvaswidth
        super(Pad, self).SetLeftMargin(margin * scale)

    def SetRightMargin(self, margin):
        canvaswidth = self.GetCanvas().GetWw() * self.GetCanvas().GetAbsWNDC()
        scale = 700.0 / canvaswidth
        super(Pad, self).SetRightMargin(margin * scale)

    def SetDrawLegend(self, boolean):
        self._drawlegend = boolean

    def SetLegendXShift(self, value):
        self._legendxshift = value

    def GetLegendXShift(self):
        return self._legendxshift

    def SetLegendYShift(self, value):
        self._legendyshift = value

    def GetLegendYShift(self):
        return self._legendyshift

    def GetDrawLegend(self):
        return self._drawlegend

    def SetYPadding(self, value):
        self._ypadding = value

    def GetYPadding(self):
        return self._ypadding

    def SetBinLabels(self, listoflabels, axes="x"):
        for coord in axes:
            axis = {
                "x": self._frame.GetXaxis(),
                "y": self._frame.GetYaxis(),
                "z": self._frame.GetZaxis(),
            }.get(coord.lower(), None)
            for i, label in enumerate(listoflabels):
                axis.SetBinLabel(
                    (i * axis.GetNbins() / len(listoflabels)) + 1, str(label)
                )
            self._frame.LabelsOption(self._labeloption.get(coord, "h"))

    def SetLabelOption(self, option, axes="xyz"):
        for coord in axes:
            self._labeloption[coord] = option
        try:
            self._frame.LabelsOption(option)
        except:
            pass
