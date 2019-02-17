#!/usr/bin/env python2.7

import ROOT

import re

from MethodProxy import *
from Helpers import DissectProperties


@PreloadProperties
class Pad(MethodProxy, ROOT.TPad):

    _frameproperties = [
        "labelfont",
        "labelsize",
        "labelcolor",
        "titlefont",
        "titlesize",
        "titlecolor",
        "titleoffset",
    ]  # applied after frame is drawn for the first time

    def __init__(self, name="undefined", *args, **kwargs):
        MethodProxy.__init__(self)
        self._frame = None
        self._xmin = self._ymin = 1e-2
        self._xmax = self._ymax = 1.0
        self._xunits, self._yunits = None, None
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
        properties = DissectProperties(kwargs, [{"Frame": Pad._frameproperties}, self])
        # self.Draw()
        # self.DeclareProperties(
        #     **{
        #         properties["Pad"].pop(k): v
        #         for k, v in list(properties["Pad"].items())
        #         if k in ["titleoffset"]
        #     }
        # )
        self.DeclareProperties(**properties["Pad"])
        self.Draw()
        self.cd()
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
            loggger.error("Cannot set 'ymin' to {} on log-axis!".format(ymin))
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
        self.RedrawAxis()

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
            axis.SetTitleOffset(offset)
            # TODO: Uniform offset and margin values for all pad and canvas sizes?
            # Make sure to declare pad dimensions before offsets and margins...
            # scale = {
            #     "x": self.GetWh() * self.GetAbsHNDC() / float(self.GetCanvas().GetWh()),
            #     "y": self.GetWw() * self.GetAbsWNDC() / float(self.GetCanvas().GetWw()),
            # }.get(coord.lower(), 1.0)
            # axis.SetTitleOffset(offset / scale)

    def SetYPadding(self, value):
        pass
