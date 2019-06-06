#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4
from collections import defaultdict

from Pad import Pad
from Text import Text
from Legend import Legend
from Canvas import Canvas
from MethodProxy import *
from Helpers import CheckPath, DissectProperties, MephistofyObject, MergeDicts


@PreloadProperties
class Plot(MethodProxy):
    def __init__(self, **kwargs):
        MethodProxy.__init__(self)
        self._name = "Plot-{}".format(uuid4().hex[:8])
        self._npads = 1
        self._store = defaultdict(list)
        self._padproperties = defaultdict(dict)
        self._mkdirs = False
        self._style = "Classic"
        self._label = ""
        self._state = ""
        self._cme = None
        self._lumi = None
        kwargs.setdefault("template", "ATLAS")
        self.DeclareProperties(**kwargs)
        for pad in range(self._npads):
            for prop, value in Pad.GetTemplate(
                "{};{}".format(self._npads, pad)
            ).items():
                self._padproperties[pad].setdefault(prop, value)

    def GetName(self):
        return self._name

    def SetNPads(self, npads):
        self._npads = npads

    def GetNPads(self):
        return self._npads

    def AssertPadIndex(self, idx):
        assert isinstance(idx, int)
        if idx >= self._npads:
            raise IndexError(
                "Cannot register object to pad '{}': ".format(idx)
                + "Plot was initialized with 'npads={}' (default: 1)".format(
                    self._npads
                )
            )

    @MephistofyObject()
    def Register(self, object, pad=0, **kwargs):
        self.AssertPadIndex(pad)
        properties = DissectProperties(kwargs, [object, Pad])
        objclsname = object.__class__.__name__
        logger.debug(
            "Registering {} object {} ('{}') to Plot '{}'...".format(
                objclsname,
                object,
                object.GetName()
                if not object.InheritsFrom("TText")
                else object.GetTitle(),
                self.GetName(),
            )
        )
        self._padproperties[pad].update(properties["Pad"])
        try:
            for key, value in object.BuildFrame(
                **MergeDicts(self._padproperties[pad])
            ).items():
                if (
                    key.endswith("max")
                    and self._padproperties[pad].get(key, value - 1) < value
                ) or (
                    key.endswith("min")
                    and self._padproperties[pad].get(key, value + 1) > value
                ):
                    self._padproperties[pad][key] = value
                if key.endswith("title"):
                    tmpltval = self._padproperties[pad].get(key, None)
                    if self._padproperties[pad].get(key, tmpltval) == tmpltval:
                        self._padproperties[pad][key] = value
        except AttributeError:
            logger.debug(
                "Cannot infer frame value ranges from {} object '{}'".format(
                    objclsname, object.GetName()
                )
            )
        self._store[pad].append((object, properties[objclsname]))
        self._padproperties[pad].update(properties["Pad"])

    def SetMkdirs(self, boolean):
        self._mkdirs = boolean

    def GetMkdirs(self):
        return self._mkdirs

    def SetStyle(self, style):
        self._style = style
        ROOT.gROOT.SetStyle(style)
        if style == "ATLAS":
            ROOT.gStyle.SetErrorX(0.5)

    def GetStyle(self):
        return self._style

    def SetLabel(self, label):
        self._label = label

    def GetLabel(self):
        return self._label

    def SetState(self, state):
        self._state = state

    def GetState(self):
        return self._state

    def SetCME(self, cme):
        self._cme = cme

    def GetCME(self):
        return self._cme

    def SetLuminosity(self, lumi):
        self._lumi = lumi

    def GetLuminosity(self):
        return self._lumi

    def GetPadHeight(self, pad=0):
        self.AssertPadIndex(pad)
        x1, y1, x2, y2 = self._padproperties[pad]["padposition"]
        return y2 - y1

    def GetPadWidth(self, pad=0):
        self.AssertPadIndex(pad)
        x1, y1, x2, y2 = self._padproperties[pad]["padposition"]
        return x2 - x1

    def AddPlotDecorations(self, refx=0.18, refy=0.935):
        # Maybe make the ref points a property?
        # Watch out, some highly phenomenological scaling ahead...
        refy += (
            (ROOT.gPad.GetTopMargin() - ROOT.gPad.GetBottomMargin())
            * 175.0
            / (ROOT.gPad.GetWh() * ROOT.gPad.GetAbsHNDC())
            / (
                self._padproperties[0]["padposition"][3]
                - self._padproperties[0]["padposition"][1]
            )
        )
        label = None
        if self._label:
            label = Text(refx, refy, "{} ".format(self._label), textfont=73)
            self.Register(label)
        if self._state:
            if label:
                state = Text(label.GetX() + label.GetXsize(), label.GetY(), self._state)
                self.Register(state)
            else:
                self.Register(Text(refx, refy, self._state))
        if self._cme:
            cmestr = "#sqrt{{s}} = {} TeV".format(self._cme)
            if self._lumi:
                cmestr += ", {} fb^{{-1}}".format(self._lumi)
            if label:
                cme = Text(
                    label.GetX(),
                    label.GetY() - 1.75 * label.GetYsize(),
                    cmestr,
                    indicesize=1.5,
                )
                self.Register(cme)
            else:
                self.Register(Text(refx, refy, cmestr))
        elif self._lumi:
            logger.error(
                "Please specify a center-of-mass energy associated to the"
                "given luminosity of {} fb^-1!".format(self._lumi)
            )

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        properties = DissectProperties(kwargs, [Plot, Canvas])
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        canvas = Canvas(
            "{}_Canvas".format(self._name),
            template=str(self._npads),
            **properties["Canvas"]
        )
        legend = {}
        self.DeclareProperties(**properties["Plot"])
        self.AddPlotDecorations()
        for i, store in self._store.items():
            pad = Pad("{}_Pad-{}".format(canvas.GetName(), i), **self._padproperties[i])
            pad.Draw()
            pad.cd()
            legend[i] = Legend(
                "{}_Legend".format(pad.GetName()),
                xshift=pad.GetLegendXShift(),
                yshift=pad.GetLegendYShift(),
            )
            canvas.SetSelectedPad(pad)
            for obj, objprops in store:
                with UsingProperties(obj, **objprops):
                    if any([obj.InheritsFrom(tcls) for tcls in ["TH1", "THStack"]]):
                        legend[i].Register(obj)
                    suffix = "SAME" if pad.GetDrawFrame() else ""
                    obj.Draw(obj.GetDrawOption() + suffix)
            if pad.GetDrawFrame():
                pad.RedrawAxis()
            if pad.GetDrawLegend():
                legend[i].Draw("SAME")
            canvas.cd()
        canvas.Print(path)
        logger.info("Created plot: '{}'".format(path))
        canvas.Delete()


if __name__ == "__main__":

    from Histo1D import Histo1D
    from IOManager import IOManager

    filename = "../data/ds_data18.root"
    logy = True

    h1 = ROOT.TH1D("test1", "TITLE_1", 20, 0.0, 400.0)
    h2 = ROOT.TH1D("test2", "TITLE_2", 20, 0.0, 400.0)
    h3 = ROOT.TH1D("test3", "TITLE_3", 20, 0.0, 400.0)
    IOManager.FillHistogram(
        h1, filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650"
    )
    IOManager.FillHistogram(
        h2, filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>750"
    )
    IOManager.FillHistogram(
        h3, filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>550"
    )

    p1 = Plot(npads=1)
    p1.Register(h1, 0, template="signal", logy=logy, xunits="GeV")
    p1.Register(h2, 0, template="signal", logy=logy, xunits="GeV")
    p1.Register(h3, 0, template="signal", logy=logy, xunits="GeV")
    p1.Register(h1, 0, template="signal", logy=logy, xunits="GeV")
    p1.Register(h2, 0, template="signal", logy=logy, xunits="GeV")
    p1.Register(h3, 0, template="signal", logy=logy, xunits="GeV")
    p1.Print("plot_test1.pdf", luminosity=139)

    p2 = Plot(npads=2)
    p2.Register(h1, 0, template="background", logy=logy, xunits="GeV")
    p2.Register(h2, 1, template="signal", xunits="GeV")
    p2.Print("plot_test2.pdf", luminosity=139)

    p3 = Plot(npads=3)
    p3.Register(h1, 0, template="background", logy=logy, xunits="GeV")
    p3.Register(h2, 1, template="signal", logy=logy, xunits="GeV")
    p3.Register(
        h3,
        2,
        template="data",
        logy=logy,
        xunits="GeV",
        ytitle="YTITLE",
        xtitle="XTITLE",
    )
    p3.Print("plot_test3.pdf", luminosity=139)
