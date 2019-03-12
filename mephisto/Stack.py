#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from Histo1D import Histo1D
from Helpers import DissectProperties, MephistofyObject, MergeDicts


def ExtendProperties(cls):
    # Add properties to configure the _stacksumhisto member histogram of Stacks.
    cls._properties += ["stacksum{}".format(p) for p in Histo1D._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Stack(MethodProxy, ROOT.THStack):

    def __init__(self, name=uuid4().hex[:8], *args, **kwargs):
        MethodProxy.__init__(self)
        self._stacksumhisto = None
        self._stacksumproperties = {}
        self._stacksorting = None
        self._drawoption = ""
        self._drawstacksum = False
        self._store = dict(stack=[], nostack=[])
        if len(args) == 0:
            ROOT.THStack.__init__(self, name, "")
        elif len(args) == 1:
            if isinstance(args[0], str):
                ROOT.THStack.__init__(self, name, args[0])
            elif args[0].InheritsFrom("THStack"):
                ROOT.THStack.__init__(self, args[0])
                self.SetName(name)
                if args[0]._stacksumhisto is not None:
                    self._stacksumhisto = Histo1D("{}_stacksum", args[0]._stacksumhisto)
            else:
                raise TypeError
        else:
            raise TypeError
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        properties = DissectProperties(kwargs, [{"Stacksum": ["stacksum{}".format(p) for p in Histo1D.GetListOfProperties()]}, self])
        self.DeclareProperties(**properties["Stack"])
        self._stacksumproperties = properties["Stacksum"]

    def DeclareProperty(self, property, args):
        # Properties starting with "stacksum" will be applied to self._stacksumhisto.
        # All stacksum properties will be applied after the main stack properties.
        property = property.lower()
        if property.startswith("stacksum"):
            self._stacksumhisto.DeclareProperty(property[8:], args)
        else:
            super(Stack, self).DeclareProperty(property, args)

    def AddStackSortingProperty(self, property, reverse=False):
        if self._stacksorting is None:
            self._stacksorting = []
        self._stacksorting.append((property, reverse))

    def SetStackSorting(self, *listoftuples):
        for property, reverse in listoftuples:
            self.AddStackSortingProperty(property, reverse)

    def GetStackSorting(self):
        return self._stacksorting

    @MephistofyObject()
    def Register(self, histo, **kwargs):
        stack = kwargs.pop("stack", False)
        if stack:
            if self._stacksumhisto is None:
                self._stacksumhisto = Histo1D("{}_totalstack".format(self.GetName()), histo)
            else:
                self._stacksumhisto.Add(histo)
        with UsingProperties(histo, **kwargs):
            self._store["stack" if stack else "nostack"].append((Histo1D("{}_{}".format(histo.GetName(), uuid4().hex[:8]), histo), kwargs))

    def BuildStack(self):
        if self._stacksorting is not None:
            for prop, reverse in reversed(self._stacksorting):
                if prop in [m.lower() for m in Histo1D._properties]:
                    self._store["stack"].sort(key=lambda tpl: tpl[0].GetProperty(prop), reverse=reverse)
                else:
                    try:
                        self._store["stack"].sort(key=lambda tpl: getattr(tpl[0], prop.capitalize()), reverse=reverse)
                    except AttributeError:
                        logger.error("Sorting failed: 'Histo1D' has no attribute '{}'!".format(prop.capitalize()))
                        raise AttributeError
        if self.GetNhists() == 0:
            for histo, properties in self._store["stack"]:
                self.Add(histo, histo.GetDrawOption())
        self.DeclareProperties(**self._stacksumproperties)

    def BuildFrame(self, **kwargs):
        frame = {}
        for histo in [self._stacksumhisto] + [h for h, p in self._store["nostack"]]:
            if not frame:
                frame = histo.BuildFrame(**kwargs)
            else:
                for key, func in [("xmin", min), ("ymin", min), ("xmax", max), ("ymax", max)]:
                    frame[key] = func(frame[key], histo.BuildFrame(**kwargs)[key])
        return frame

    def Print(self, path, **kwargs):
        self.BuildStack()
        properties = DissectProperties(kwargs, [Stack, Plot, Canvas, Pad])
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Stack"], properties["Pad"]))
        for histo, histoprops in self._store["nostack"]:
            plot.Register(histo, **MergeDicts(histoprops, properties["Pad"]))
        plot.Print(path, **MergeDicts(properties["Plot"], properties["Canvas"]))

    def SetDrawOption(self, option):
        # For some reason a THStack must be drawn with "SAMESAME" in the drawoption...
        # For "LEGO" and "SURF" drawoption "SAME" must not be added and the pad should
        # best be initialized with the "drawframe" property set to False!
        self._drawoption = option
        if not any(opt in self._drawoption.upper() for opt in ["LEGO", "SURF"]):
            self._drawoption += "SAME"
        super(Stack, self).SetDrawOption(option)

    def GetDrawOption(self):
        return self._drawoption

    def SetDrawStackSum(self, boolean):
        self._drawstacksum = boolean

    def GetDrawStackSum(self):
        return self._drawstacksum

    def Draw(self, drawoption=None):
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        super(Stack, self).Draw(self.GetDrawOption())
        if self._drawstacksum and self._stacksumhisto is not None:
            self._stacksumhisto.Draw(self._stacksumhisto.GetDrawOption() + "SAME")


if __name__ == '__main__':

    filename = "../data/ds_data18.root"
    h1 = Histo1D("h1", "h1", 20, 0.0, 400.0)
    h2 = Histo1D("h2", "h2", 20, 0.0, 400.0)
    h3 = Histo1D("h3", "h3", 20, 0.0, 400.0)

    h1.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>600")
    h2.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>725")
    h3.Fill(filename, tree="DirectStau", varexp="MET", cuts="tau1Pt>850")

    s = Stack()
    s.Register(h1, stack=True, template="background", fillcolor=ROOT.kBlue)
    s.Register(h2, stack=True, template="background", fillcolor=ROOT.kGreen)
    s.Register(h3, stack=False, template="signal", linecolor=ROOT.kRed)

    s.Print("test_stack.pdf", xunits="GeV")
