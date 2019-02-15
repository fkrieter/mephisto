#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from collections import defaultdict

from Pad import Pad
from Canvas import Canvas
from MethodProxy import *
from Helpers import CheckPath, DissectProperties, MephistofyObject


@PreloadProperties
class Plot(MethodProxy):
    def __init__(self, **kwargs):
        MethodProxy.__init__(self)
        self._npads = 1
        self._store = defaultdict(list)
        self._padproperties = defaultdict(dict)
        self._mkdirs = False
        self._style = "Classic"
        kwargs.setdefault("template", "ATLAS")
        self.DeclareProperties(**kwargs)

    def SetNPads(self, npads):
        self._npads = npads

    def GetNPads(self):
        return self._npads

    @MephistofyObject()
    def Register(self, object, pad=0, **kwargs):
        assert isinstance(pad, int)
        if pad >= self._npads:
            raise IndexError(
                "Cannot register object '{}' to pad '{}': ".format(
                    object.GetName(), pad
                )
                + "Plot was initialized with 'npads={}' (default: 1)".format(
                    self._npads
                )
            )
        properties = DissectProperties(kwargs, [object, Pad])
        properties["Pad"]["template"] = "{};{}".format(self._npads, pad)
        objclsname = object.__class__.__name__
        if set(properties[objclsname].keys()) & set(["xtitle", "ytitle"]):
            properties["Pad"].setdefault(
                "title",
                ";{};{}".format(
                    properties[objclsname].get("xtitle", ""),
                    properties[objclsname].get("ytitle", ""),
                ),
            )
        for key in ["logx", "logy"]:
            self._padproperties[pad].setdefault(
                key, Pad.GetTemplate(properties["Pad"]["template"])[key]
            )
            if key in properties["Pad"].keys():
                self._padproperties[pad][key] = properties["Pad"][key]
            else:
                properties["Pad"].setdefault(key, self._padproperties[pad][key])
        try:
            for key, value in object.BuildFrame(**properties["Pad"]).items():
                if (
                    key.endswith("max")
                    and self._padproperties[pad].get(key, value - 1) < value
                ) or (
                    key.endswith("min")
                    and self._padproperties[pad].get(key, value + 1) > value
                ):
                    self._padproperties[pad][key] = value
        except AttributeError:
            logger.warning(
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

    def GetStyle(self):
        return self._style

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        properties = DissectProperties(kwargs, [Plot, Canvas])
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetPaintTextFormat("4.2f")
        npads = len(self._store)
        canvas = Canvas("test", template=str(npads), **properties["Canvas"])
        for i, store in self._store.items():
            pad = Pad("{}_pad{}".format(canvas.GetName(), i), **self._padproperties[i])
            pad.DrawFrame()
            canvas.SetSelectedPad(pad)
            for obj, properties in store:
                with UsingProperties(obj, **properties):
                    obj.Draw(obj.GetDrawOption() + "same")
                # legend = pad.BuildLegend()
                # legend.Draw(suffix)
            pad.RedrawAxis()
        canvas.Print(path)
        logger.info("Created plot: '{}'".format(path))
        canvas.Delete()


if __name__ == "__main__":

    from Histo1D import Histo1D
    from iomanager import iomanager

    filename = "../data/ds_data18.root"

    # h1 = Histo1D("test1", 20, 0.0, 400.0)
    # h2 = Histo1D("test2", 20, 0.0, 400.0)
    # h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650")
    # h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>750")

    h1 = ROOT.TH1D("test1", "", 20, 0.0, 400.0)
    h2 = ROOT.TH1D("test2", "", 20, 0.0, 400.0)
    iomanager.fill_histo(
        h1, filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>650"
    )
    iomanager.fill_histo(
        h2, filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>750"
    )

    p = Plot()
    p.Register(h1, 0, template="background", logy=False)
    p.Register(h2, 0, template="signal")
    p.Print("plot_test.pdf")
