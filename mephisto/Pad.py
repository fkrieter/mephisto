#!/usr/bin/env python2.7

import ROOT

from MethodProxy import *


@PreloadProperties
class Pad(MethodProxy, ROOT.TPad):
    def __init__(self, name="undefined", *args, **kwargs):
        self._xmin = self._ymin = 1e-2
        self._xmax = self._ymax = 1.0
        MethodProxy.__init__(self)
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
        self.DeclareProperties(**kwargs)
        self.Draw()
        self.cd()

    def SetPadPosition(self, xlow, ylow, xup, yup):
        self._xposlow, self._yposlow = xlow, ylow
        self._xposup, self._yposup = xup, yup
        self.SetPad(xlow, ylow, xup, yup)

    def GetPadPosition(self):
        return (self._xposlow, self._yposlow, self._xposup, self._yposup)

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
            raise ValueError("Cannot set 'xmin' to {} on log-axis!".format(xmin))
        self._xmin = xmin

    def SetXMax(self, xmax):
        if self.GetLogx() and xmax <= 0:
            raise ValueError("Cannot set 'xmax' to {} on log-axis!".format(xmax))
        self._xmax = xmax

    def SetYMin(self, ymin):
        if self.GetLogy() and ymin <= 0:
            raise ValueError("Cannot set 'ymin' to {} on log-axis!".format(ymin))
        self._ymin = ymin

    def SetYMax(self, ymax):
        if self.GetLogx() and ymax <= 0:
            raise ValueError("Cannot set 'ymax' to {} on log-axis!".format(ymax))
        self._ymax = ymax

    def SetLogx(self, boolean):
        if boolean and self.GetXMin() * self.GetXMax() <= 0:
            raise ValueError(
                "Cannot set 'logx' to '{}' on axis with negative"
                " values!".format(boolean)
            )
        super(Pad, self).SetLogx(boolean)

    def SetLogy(self, boolean):
        if boolean and self.GetYMin() * self.GetYMax() <= 0:
            raise ValueError(
                "Cannot set 'logy' to '{}' on axis with negative"
                " values!".format(boolean)
            )
        super(Pad, self).SetLogy(boolean)

    def DrawFrame(self, *args):
        if len(args) == 4:
            for i, prop in enumerate(["xmin", "ymin", "xmax", "ymax"]):
                self.DeclareProperty(prop, args[i])
        elif len(args) != 0:
            raise TypeError(
                "DrawFrame() takes exactly 0 or 4 arguments"
                " ({} given)".format(len(args))
            )
        assert self._xmin < self._xmax
        assert self._ymin < self._ymax
        super(Pad, self).DrawFrame(
            self._xmin, self._ymin, self._xmax, self._ymax, self.GetTitle()
        )
