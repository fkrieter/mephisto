#!/usr/bin/env python2.7

import ROOT

from MethodProxy import MethodProxy


class Pad(MethodProxy, ROOT.TPad):

    def __init__(self, name="undefined", *args, **kwargs):
        MethodProxy.__init__(self)
        if len(args) > 0:
            self._xlow, self._ylow = args[0:2]
            self._xup, self._yup = args[2:4]
            ROOT.TPad.__init__(self, name, "", *args)
        else:
            self._xlow, self._ylow, self._xup, self._yup = 0., 0., 1., 1.
            ROOT.TPad.__init__(self)
            self.SetName(name)
        self.DeclareProperties(**kwargs)
        self.Draw()
        self.cd()

    def SetPadPosition(self, xlow, ylow, xup, yup):
        self._xlow, self._ylow = xlow, ylow
        self._xup, self._yup = xup, yup
        self.SetPad(xlow, ylow, xup, yup)

    def GetPadPosition(self):
        return (self._xlow, self._ylow, self._xup, self._yup)
