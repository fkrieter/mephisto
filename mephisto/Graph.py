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
    r"""Class for displaying arrays of 2-dimensional coordinates.

    +---------------------------------------------------------------------------------+
    | Inherits from :class:`ROOT.TGraphAsymmErrors`, see official                     |
    | `documentation <https://root.cern.ch/doc/master/classTGraphAsymmErrors.html>`_  |
    | as well!                                                                        |
    +---------------------------------------------------------------------------------+

    In order to avoid memory leaks, **name** is an inaccessible property despite having
    corresponding getter and setter methods. Furthermore the properties **xtitle**,
    **ytitle** and **ztitle** are defined to be exclusive to the :class:`.Pad` class.
    """

    _ignore_properties = ["name", "point", "xtitle", "ytitle", "ztitle"]

    def __init__(self, name="Graph_{}".format(uuid4().hex[:8]), *args, **kwargs):
        r"""Initialize a graph.

        Create an instance of :class:`.Graph` with the specified **name** from two
        arrays of equal length.

        :param name: name of the graph
        :type name: ``str``

        :param \*args: see below

        :param \**kwargs: :class:`.Graph` properties

        :Arguments:
            The first and optional argument is **title** of the graph given by a
            ``str``.

            Depending on the total number of arguments (besides **name** and the
            optional **title**) there are two ways to initialize a :class:`.Graph`
            object\:

            * *one* argument\:

                #. **graph** (``Graph``, ``TGraph``, ``TGraphAsymmErrors``) -- graph to
                   be copied

            * *two* arguments\:

                #. **xvalues** (``list``) -- list of x-values which can be either of
                   type ``float`` or ``tuple``/``list``; in the latter case depending
                   on the length of the ``tuple``/``list`` the entries are interpreted
                   as\:

                        #. nominal x-value

                        #. nominal x-value, (sym.) uncertainty

                        #. nominal x-value, up-, down-uncertainty

                #. **yvalues** (``list``) -- list of y-values which can be either of
                   type ``float`` or ``tuple``/``list`` (see above)
        """
        MethodProxy.__init__(self)
        self._name = name
        self._title = ""
        if isinstance(args[0], (str, unicode)):
            self._title = args[0]
            args = args[1:]
        self._drawoption = ""
        if len(args) == 1 and args[0].InheritsFrom("TGraph"):
            if args[0].InheritsFrom("TGraphAsymmErrors"):
                ROOT.TGraphAsymmErrors.__init__(self, args[0])
            elif isinstance(args[0], ROOT.TGraph):
                x, y = array("d", []), array("d", [])
                for i in range(args[0].GetN()):
                    x_i = ROOT.Double(0.0)
                    y_i = ROOT.Double(0.0)
                    args[0].GetPoint(i, x_i, y_i)
                    x.append(x_i)
                    y.append(y_i)
                ROOT.TGraphAsymmErrors.__init__(self, args[0].GetN(), x, y)
            else:
                raise NotImplementedError
        elif len(args) == 2:
            if not all([isinstance(a, list) for a in args]):
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
            for key, value in self.GetTemplate(
                kwargs.get("template", "common")
            ).items():
                kwargs.setdefault(key, value)
        else:
            raise TypeError
        self.SetName(self._name)
        self.SetTitle(self._title)
        self.DeclareProperties(**kwargs)

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        r"""Print the graph to a file.

        Creates a PDF/PNG/... file with the absolute path defined by **path**. If a file
        with the same name already exists it will be overwritten (can be changed  with
        the **overwrite** keyword argument). If **mkdir** is set to ``True`` (default:
        ``False``) directories in **path** with do not yet exist will be created
        automatically. The styling of the graph, pad and canvas can be configured via
        their respective properties passed as keyword arguments.

        :param path: path of the output file (must end with '.pdf', '.png', ...)
        :type path: ``str``

        :param \**kwargs: :class:`.Graph`, :class:`.Plot`, :class:`.Canvas` and
            :class:`.Pad` properties + additional properties (see below)

        Keyword Arguments:

            * **inject** (``list``, ``tuple``, ``ROOT.TObject``) -- inject a (list of)
              *drawable* :class:`ROOT` object(s) to the main pad, object properties can
              be specified by passing instead a ``tuple`` of the format
              :code:`(obj, props)` where :code:`props` is a ``dict`` holding the object
              properties (default: \[\])

            * **overwrite** (``bool``) -- overwrite an existing file located at **path**
              (default: ``True``)

            * **mkdir** (``bool``) -- create non-existing directories in **path**
              (default: ``False``)
        """
        injections = {"inject0": kwargs.pop("inject", [])}
        properties = DissectProperties(kwargs, [Graph, Plot, Canvas, Pad])
        properties["Pad"].setdefault("logy", False)
        plot = Plot(npads=1)
        plot.Register(self, **MergeDicts(properties["Graph"], properties["Pad"]))
        plot.Print(
            path, **MergeDicts(properties["Plot"], properties["Canvas"], injections)
        )

    def SetDrawOption(self, option):
        r"""Define the draw option for the graph.

        :param option: draw option (see :class:`ROOT.TGraphPainter`
            `class reference <https://root.cern/doc/master/classTGraphPainter.html>`_)
        :type option: ``str``
        """
        self._drawoption = option
        super(Graph, self).SetDrawOption(option)

    def GetDrawOption(self):
        r"""Return the draw option defined for the graph.

        :returntype: ``str``
        """
        return self._drawoption

    def Draw(self, option=None):
        # Draw the graph to the current TPad together with it's errorband.
        # TODO: Maybe find a way to avoid the creation of the _tmpgraph object :-/
        # Unfortunately there's no DrawCopy method for TGraphs and DrawClone doesn't
        # work propertly either...
        if option is not None:
            self.SetDrawOption(option)
        option = self.GetDrawOption().upper().replace("SAME", "")
        self._tmpgraph = Graph("{}_{}".format(self.GetName(), uuid4().hex[:8]), self)
        search = re.search("(?P<ERROPT>[2-5])", option)
        if search is not None:
            erropt = search.group("ERROPT")
            super(Graph, self._tmpgraph).Draw("{}".format(erropt))
            for rmv in ["A", "F", erropt]:
                option = option.replace(rmv, "")
            super(Graph, self._tmpgraph).Draw(option + "X")
        else:
            super(Graph, self._tmpgraph).Draw(option)

    def GetPoint(self, index, *args):
        r"""Return the x- and y-value for a given index if no other arguments are given.
        Otherwise the standard :func:`ROOT.TGraph.GetPoint` functionality is used.

        :param index: index of the coordinate point
        :type index: ``int``

        :param \*args: see :py:mod:`ROOT` documentation of :func:`ROOT.TGraph.GetPoint`

        :returntype: ``tuple`` for call with no additional arguments, else ``None``
        """
        if len(args) == 0 and isinstance(index, int):
            x = ROOT.Double(0.0)
            y = ROOT.Double(0.0)
            super(Graph, self).GetPoint(index, x, y)
            return x, y
        elif len(args) == 2:
            super(Graph, self).GetPoint(*args)
        else:
            raise TypeError

    def BuildFrame(self, **kwargs):
        # Return the optimal axis ranges for the graph. Gets called by Plot when the
        # graph is registered to it.
        # Note: Only works if drawoption does not contain "A".
        scale = 1.0 + kwargs.get("ypadding", 0.25)  # Pad property
        logx = kwargs.get("logx", False)
        logy = kwargs.get("logy", False)
        frame = {"xmin": None, "xmax": 0, "ymin": 0, "ymax": 0}
        for i in range(self.GetN()):
            x, y = self.GetPoint(i)
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
        frame["xtitle"] = kwargs.get("xtitle", None)
        frame["ytitle"] = kwargs.get("ytitle", None)
        return frame


def main():

    g = Graph(
        "test",
        "title",
        [1.0, 2.0, 3.0],
        [(3.0, 0.5, 0.8), (2.5, 0.4, 0.5), (1.0, 0.1, 0.1)],
    )
    g.Print("test_graph.pdf", linecolor=ROOT.kBlue)


if __name__ == "__main__":
    main()
