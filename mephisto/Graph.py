#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

import re

from uuid import uuid4
from array import array
from collections import defaultdict

from Pad import Pad
from Plot import Plot
from MethodProxy import *
from Canvas import Canvas
from Helpers import DissectProperties, MergeDicts, CheckPath


@PreloadProperties
class Graph(MethodProxy, ROOT.TGraphAsymmErrors):

    _ignore_properties = ["name", "point"]

    def __init__(self, name="Graph_{}".format(uuid4().hex[:8]), *args, **kwargs):
        MethodProxy.__init__(self)
        self._name = name
        self._title = ""
        if isinstance(args[0], (str, unicode)):
            self._title = args[0]
            args = args[1:]
        self._drawoption = ""
        if len(args) == 2:
            if not all([isinstance(a, (list, tuple)) for a in args]):
                raise TypeError
            if not len(args[0]) == len(args[1]):
                logger.error(
                    "Number of x-values ({}) does not match number of "
                    "y-values ({})!".format(len(args[0]), len(args[1]))
                )
                raise TypeError
            val = dict(x={}, y={})
            for idx, coord in enumerate(["x", "y"]):
                for var in ["nominal", "errorup", "errordown"]:
                    val[coord][var] = array("d", [])
                for tpl in args[idx]:
                    if isinstance(tpl, (list, tuple)):
                        if len(tpl) == 1:
                            val[coord]["nominal"].append(tpl[0])
                            val[coord]["errorup"].append(0.0)
                            val[coord]["errordown"].append(0.0)
                        elif len(tpl) == 2:  # errorup = errordown
                            val[coord]["nominal"].append(tpl[0])
                            val[coord]["errorup"].append(tpl[1])
                            val[coord]["errordown"].append(tpl[1])
                        elif len(tpl) == 3:
                            val[coord]["nominal"].append(tpl[0])
                            val[coord]["errorup"].append(tpl[1])
                            val[coord]["errordown"].append(tpl[2])
                        else:
                            raise TypeError
                    elif isinstance(tpl, (int, float)):
                        val[coord]["nominal"].append(tpl)
                        val[coord]["errorup"].append(0.0)
                        val[coord]["errordown"].append(0.0)
                    else:
                        raise TypeError
            ROOT.TGraphAsymmErrors.__init__(
                self,
                len(args[0]),
                val["x"]["nominal"],
                val["y"]["nominal"],
                val["x"]["errordown"],
                val["x"]["errorup"],
                val["y"]["errordown"],
                val["y"]["errorup"],
            )
            self.SetTitle(self._title)
        else:
            raise TypeError
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        self.DeclareProperties(**kwargs)

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        injections = {"inject0": kwargs.pop("inject", [])}
        properties = DissectProperties(kwargs, [Graph, Plot, Canvas, Pad])
        properties["Pad"].setdefault("logy", False)
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Graph"], properties["Pad"]))
        plot.Print(
            path, **MergeDicts(properties["Plot"], properties["Canvas"], injections)
        )

    def SetDrawOption(self, option):
        self._drawoption = option
        super(Graph, self).SetDrawOption(option)

    def GetDrawOption(self):
        return self._drawoption

    def Draw(self, option=None):
        if option is not None:
            self.SetDrawOption(option)
        option = self.GetDrawOption().upper().replace("SAME", "")
        search = re.search("(?P<ERROPT>[2-5])", option)
        if search is not None:
            erropt = search.group("ERROPT")
            super(Graph, self).Draw("A{}".format(erropt))
            for rmv in ["A", "F", erropt]:
                option = option.replace(rmv, "")
            super(Graph, self).Draw(option + "X")
        else:
            super(Graph, self).Draw(option)

    def GetPoint(self, *args):
        if len(args) == 1 and isinstance(args[0], int):
            x = ROOT.Double(0.0)
            y = ROOT.Double(0.0)
            super(Graph, self).GetPoint(args[0], x, y)
            return x, y
        else:
            super(Graph, self).GetPoint(*args)

    def BuildFrame(self, **kwargs):
        # Note: Only works if drawoption does not contain "A".
        scale = 1.0 + kwargs.get("ypadding", 0.25)  # Pad property
        logx = kwargs.get("logx", False)
        logy = kwargs.get("logy", False)
        xtitle = kwargs.get("xtitle", None)
        ytitle = kwargs.get("ytitle", None)
        frame = {"xmin": None, "xmax": 0, "ymin": 0, "ymax": 0}
        for i in range(self.GetN()):
            print(i)
            x, y = self.GetPoint(i)
            print(x, y)
            frame["xmin"] = min(x, frame["xmin"]) if frame["xmin"] is not None else x
            frame["xmax"] = max(x, frame["xmax"])
            frame["ymin"] = min(y, frame["ymin"])
            frame["ymax"] = max(y, frame["ymax"])
        if logx and frame["xmin"] <= 0:
            frame["xmin"] = kwargs.get("xmin", 1e-2)
        if logy and frame["ymin"] <= 0:
            frame["ymin"] = kwargs.get("ymin", 1e-2)
            frame["ymax"] = 10 ** (
                scale * ROOT.TMath.Log10(frame["ymax"] / frame["ymin"])
                + ROOT.TMath.Log10(frame["ymin"])
            )
        else:
            frame["ymax"] *= scale
        return frame


def main():

    g = Graph(
        "test",
        "title",
        [1.0, 2.0, 3.0],
        [(3.0, 0.5, 0.8), (2.5, 0.4, 0.5), (1.0, 0.1, 0.1)],
    )
    g.Print("test_graph.pdf")


if __name__ == "__main__":
    main()
