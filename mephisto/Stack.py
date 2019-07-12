#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from uuid import uuid4
from distutils.spawn import find_executable

from Pad import Pad
from Plot import Plot
from Canvas import Canvas
from MethodProxy import *
from Histo1D import Histo1D
from Helpers import CheckPath, DissectProperties, MephistofyObject, MergeDicts, TeX2PDF


def ExtendProperties(cls):
    # Add properties to configure the _stacksumhisto member histogram of Stacks.
    cls._properties += ["stacksum{}".format(p) for p in Histo1D._properties]  # append!
    return cls


@ExtendProperties
@PreloadProperties
class Stack(MethodProxy, ROOT.THStack):
    r"""Class for a stack of 1-dimensional histograms.

    +-------------------------------------------------------------------------------+
    | Inherits from :class:`ROOT.THStack`, see                                      |
    | official `documentation <https://root.cern.ch/doc/master/classTHStack.html>`_ |
    | as well!                                                                      |
    +-------------------------------------------------------------------------------+

    Collect multiple 1-dimensional histograms in a :class:`.Stack` object. Print stacked
    histograms and overlay unstacked histograms, e.g. for data or signal vs. background
    plots. Other plots can be added to :class:`.Pad` s below the main one where the
    :class:`.Stack` object is drawn, see the :func:`~Stack.Print` method.

    The properties of the **stacksum** object (which is of type ``Histo1D``), which
    represents the sum of all stacked histograms, can be accessed by prepending the
    prefix 'stacksum' in front of the property name.

    In order to avoid memory leaks, **name** and **histogram** are inaccessible
    properties despite having corresponding getter and setter methods. Furthermore the
    properties **xtitle**, **ytitle** and **ztitle** are defined to be exclusive to the
    :class:`.Pad` class.
    """

    _ignore_properties = ["name", "xtitle", "ytitle", "ztitle", "histogram"]

    def __init__(self, name=uuid4().hex[:8], *args, **kwargs):
        r"""Initialize a collection of 1-dimensional histograms.

        Create an instance of :class:`.Stack` with the specified **name**. Can also be
        used to copy another histogram (or upgrade from a :class:`ROOT.THStack`).

        :param name: name of the stack (default: random 8-digits HEX hash value)
        :type name: ``str``

        :param \*args: see below

        :param \**kwargs: :class:`.Stack` properties

        :Arguments:
            Depending on the number of arguments (besides **name**) there are two ways
            to initialize a :class:`.Stack` object\:

            * *zero* arguments\: an empty stack is created

            * *one* argument\:

                #. **stack** (``Stack``, ``THStack``) -- existing stack to be copied
        """
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
                if args[0].__class__.__name__ == "Stack":
                    if args[0]._stacksumhisto is not None:
                        self._stacksumhisto = Histo1D(
                            "{}_stacksum", args[0]._stacksumhisto
                        )
                    for key, store in args[0]._store.items():
                        for histo in store:
                            self._store[key].append(
                                Histo1D("{}_{}".format(histo.GetName(), name), histo)
                            )
                    self.DeclareProperties(**args[0].GetProperties())
            else:
                raise TypeError
        else:
            raise TypeError
        for key, value in self.GetTemplate(kwargs.get("template", "common")).items():
            kwargs.setdefault(key, value)
        properties = DissectProperties(
            kwargs,
            [
                {
                    "Stacksum": [
                        "stacksum{}".format(p) for p in Histo1D.GetListOfProperties()
                    ]
                },
                Stack,
            ],
        )
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

    def GetProperty(self, property):
        # If the property starts with "stacksum" return the associated property of the
        # self._stacksumhisto.
        if property.startswith("stacksum"):
            return self._stacksumhisto.GetProperty(property[8:])
        else:
            super(Stack, self).GetProperty(property)

    @MephistofyObject(copy=True)
    def Register(self, histo, **kwargs):
        r"""Register a histogram to the stack.

        If the **stack** keyword arguments (or the associated property of the
        :class:`.Histo1D` **histo**) is ``True`` the **histo** will be drawn in a stack.
        Otherwise the histogram will be displayed overlayed to the stack.

        The properties of the **histo** registered to the stack can be changed by simply
        passing them as keyword arguments.

        :param histo: histogram to be added to the :class:`.Stack` object
        :type histo: ``Histo1D``, ``TH1D``

        :param \**kwargs: :class:`.Histo1D` properties + additional properties (see
            below)

        :Keyword Arguments:

            * **stack** (``bool``) -- if set to ``True`` the histogram will be displayed
              in the stack of all stacked histograms
        """
        stack = kwargs.pop("stack", histo.GetStack())
        histo.SetDrawErrorband(False)
        if stack:
            if self._stacksumhisto is None:
                self._stacksumhisto = Histo1D(
                    "{}_totalstack".format(self.GetName()),
                    histo,
                    title=self._stacksumproperties.get("stacksumtitle", None),
                )
            else:
                self._stacksumhisto.Add(histo)
        histo.DeclareProperties(**kwargs)
        self._store["stack" if stack else "nostack"].append(histo)

    def SortStack(self):
        # Sort the stack according to self._stacksorting.
        if self._stacksorting is not None:
            for prop, reverse in reversed(self._stacksorting):
                if prop in [m.lower() for m in Histo1D._properties]:
                    self._store["stack"].sort(
                        key=lambda h: h.GetProperty(prop), reverse=reverse
                    )
                else:
                    try:
                        self._store["stack"].sort(
                            key=lambda h: getattr(h, prop.capitalize())(),
                            reverse=reverse,
                        )
                    except AttributeError:
                        logger.error(
                            "Sorting failed: 'Histo1D' has no attribute '{}'!".format(
                                prop.capitalize()
                            )
                        )
                        raise AttributeError

    def BuildStack(self, **kwargs):
        # Build the actual THStack.
        if self.GetNhists() != 0:
            return
        if kwargs.get("sort", True):
            self.SortStack()
        for histo in self._store["stack"]:
            self.Add(histo, histo.GetDrawOption())
        self.DeclareProperties(**self._stacksumproperties)

    def BuildFrame(self, **kwargs):
        # Return the optimal axis ranges for the stack. Gets called by Plot when the
        # stack is registered to it.
        logy = kwargs.get("logy", False)
        frame = {}
        for histo in [self._stacksumhisto] + self._store["nostack"]:
            if not frame:
                frame = histo.BuildFrame(**kwargs)
            else:
                for key, func in [
                    ("xmin", min),
                    ("ymin", min),
                    ("xmax", max),
                    ("ymax", max),
                ]:
                    frame[key] = func(frame[key], histo.BuildFrame(**kwargs)[key])
        Stack.UpdateYAxisRange(self, frame["ymin"], frame["ymax"], logy)
        return frame

    @staticmethod
    def UpdateYAxisRange(stack, ymin, ymax, logy=False):
        # The THStack y-range problem is super annoying and unfortunately not fully
        # solved by drawing a pad frame first (for plots with mutliple pads the y-range
        # for the first drawn pad (with a THStack in it) is ignored).
        # So here's a fix for that:
        # (See: https://root-forum.cern.ch/t/trouble-w-stackhistograms/12390)
        if not logy:
            stack.SetMaximum(ymax / (1 + ROOT.gStyle.GetHistTopMargin()))
            stack.SetMinimum(ymin)
        else:
            stack.SetMaximum(ymax / (1 + 0.2 * ROOT.TMath.Log10(ymax / ymin)))
            stack.SetMinimum(ymin * (1 + 0.5 * ROOT.TMath.Log10(ymax / ymin)))

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        r"""Print the histogram to a file.

        Creates a PDF/PNG/... file with the absolute path defined by **path**. If a file
        with the same name already exists it will be overwritten (can be changed  with
        the **overwrite** keyword argument). If **mkdir** is set to ``True`` (default:
        ``False``) directories in **path** with do not yet exist will be created
        automatically. The styling of the stack, pad and canvas can be configured via
        their respective properties passed as keyword arguments.

        Additional plots can be added to :class:`.Pad` s below the main one where the
        :class:`.Stack` object is drawn using the **ratio**, **contribution** and/or
        **sensitivity** flag (see below).

        :param path: path of the output file (must end with '.pdf', '.png', ...)
        :type path: ``str``

        :param \**kwargs: :class:`.Stack`, :class:`.Plot`, :class:`.Canvas` and
            :class:`.Pad` properties + additional properties (see below)

        Keyword Arguments:

            * **sort** (``bool``) -- define whether the stack is sorted before it is
              drawn (see :func:`Stack.SetStackSorting`, default: ``True``)

            * **contribution** (``bool``) -- draw the relative per-bin contribution of
              each stacked histogram in an additional :class:`.Pad` (default: ``False``)

            * **ratio** (``bool``) -- draw a :class:`RatioPlot` of (assumed) data versus
              the (assumed) total background in an additional :class:`.Pad` (default:
              ``False``)
            * **sensitivity** (``bool``) -- draw a sensitivity scan for all (assumed)
              signal histograms and using the (asumed) total background as reference in
              an additional :class:`.Pad` (default: ``False``)

            * **inject<N>** (``list``, ``tuple``, ``ROOT.TObject``) -- inject a (list
              of) *drawable* :class:`ROOT` object(s) to pad **<N>** (default: 0), object
              properties can be specified by passing instead a ``tuple`` of the format
              :code:`(obj, props)` where :code:`props` is a ``dict`` holding the object
              properties (default: \[\])

            * **overwrite** (``bool``) -- overwrite an existing file located at **path**
              (default: ``True``)

            * **mkdir** (``bool``) -- create non-existing directories in **path**
              (default: ``False``)
        """
        from RatioPlot import RatioPlot
        from SensitivityScan import SensitivityScan
        from ContributionPlot import ContributionPlot

        sort = kwargs.pop("sort", True)
        contribution = kwargs.pop("contribution", False)
        ratio = kwargs.pop("ratio", False)
        sensitivity = kwargs.pop("sensitivity", False)
        injections = {
            k: kwargs.pop(k) for k in dict(kwargs).keys() if k.startswith("inject")
        }
        if ratio is True:
            try:  # it's just a guess...
                datahisto = filter(
                    lambda h: not h.GetDrawOption().upper().startswith("HIST"),
                    self._store["nostack"],
                )[0]
                ratio = [datahisto, self._stacksumhisto]  # overwrite boolean
            except IndexError:
                logger.error(
                    "Failed to identify appropriate numerator histogram for RatioPlot "
                    "pad!"
                )
                ratio = False
        if sensitivity:
            try:  # again just making assumptions here...
                sensitivity = filter(
                    lambda h: "HIST" in h.GetDrawOption().upper(),
                    self._store["nostack"],  # overwrite boolean with list of sig histos
                )
            except IndexError:
                logger.error(
                    "Failed to identify appropriate numerator histogram for RatioPlot "
                    "pad!"
                )
                sensitivity = False
        npads = sum([contribution, bool(ratio), bool(sensitivity)]) + 1
        properties = DissectProperties(kwargs, [Stack, Plot, Canvas, Pad])
        self.BuildStack(sort=sort)
        plot = Plot(npads=npads)
        # Register the Stack to the upper Pad (pad=0):
        plot.Register(self, **MergeDicts(properties["Stack"], properties["Pad"]))
        if self._drawstacksum and self._stacksumhisto.GetAddToLegend():
            # Dummy histo with the correct legend entry styling:
            htmp = Histo1D(
                "{}_legendentry".format(self._stacksumhisto.GetName()),
                self._stacksumhisto.GetTitle(),
                [0, 1],
                **{
                    k[8:]: v
                    for k, v in DissectProperties(
                        properties["Stack"],
                        [
                            {
                                "Stacksum": [
                                    "stacksum{}".format(p)
                                    for p in Histo1D.GetListOfProperties()
                                ]
                            }
                        ],
                    )["Stacksum"].items()
                }
            )
            plot.Register(
                htmp,
                fillcolor=self._stacksumhisto._errorband.GetFillColor(),
                fillstyle=self._stacksumhisto._errorband.GetFillStyle(),
                legenddrawoption=self._stacksumhisto.GetLegendDrawOption(),
                **properties["Pad"]
            )
        idx = 1
        xaxisprops = {
            k: v for k, v in properties["Pad"].items() if k in ["xtitle", "xunits"]
        }
        if contribution:
            contribplot = ContributionPlot(self)
            plot.Register(
                contribplot,
                pad=idx,
                ytitle="Contrib.",
                logy=False,
                ymin=0,
                ymax=1,
                **xaxisprops
            )
            idx += 1
        if ratio:
            ratioplot = RatioPlot(*ratio)
            plot.Register(
                ratioplot,
                pad=idx,
                ytitle="Data / SM",
                logy=False,
                ymin=0.2,
                ymax=1.8,
                **xaxisprops
            )
            idx += 1
        if sensitivity:
            sensitivityscan = SensitivityScan(sensitivity, self._stacksumhisto)
            plot.Register(
                sensitivityscan,
                pad=idx,
                ytitle="Z_{N}-value",  # default (see template 'common')
                logy=False,
                **xaxisprops
            )
        plot.Print(
            path, **MergeDicts(properties["Plot"], properties["Canvas"], injections)
        )

    @CheckPath(mode="w")
    def PrintYieldTable(self, path=None, **kwargs):
        r"""Print the yields of all registered histograms.

        If the **path** is not ``None`` the table is saved to a CSV, TEX or PDF file as
        specified by the extension.

        :param path: path of the output file (must end with '.csv', '.tex' or '.pdf',
            default: ``None``)
        :type path: ``str``

        :param \**kwargs: see below

        :Keyword argument:

            * **silent** (``bool``) -- do not print the table to ``stdout`` (default:
              ``False``)

            * **precision** (``int``) -- amount of decimals given for the yields
              (default: 2)

            * **crop** (``bool``) -- remove empty space from the final PDF file
              (default: ``True``)

            * **overwrite** (``bool``) -- overwrite an existing file located at **path**
              (default: ``True``)

            * **mkdir** (``bool``) -- create non-existing directories in **path**
              (default: ``False``)
        """
        silent = kwargs.pop("silent", False)  # don't print table to stdout
        precision = kwargs.pop("precision", 2)
        crop = kwargs.pop("crop", True)  # get a nice PDF table!
        yields = [["Process", "Yield", "Stat. error", "Raw"]]
        for histo in (
            sorted(
                self._store["stack"],
                key=lambda h: h.Integral(0, h.GetNbinsX() + 1),
                reverse=True,
            )
            + [self._stacksumhisto]
            + sorted(
                self._store["nostack"],
                key=lambda h: h.Integral(0, h.GetNbinsX() + 1),
                reverse=True,
            )
        ):
            staterr = ROOT.Double(0)
            integral = "{:.{prec}f}".format(
                histo.IntegralAndError(0, histo.GetNbinsX() + 1, staterr),
                prec=precision,
            )
            staterr = "{:.{prec}f}".format(staterr, prec=precision)
            raw = str(int(histo.GetEntries()))
            yields.append([histo.GetTitle(), integral, staterr, raw])
        colwidths = [
            max(w) for w in zip(*[[len(str(e)) for e in entries] for entries in yields])
        ]
        if not silent:
            for i, row in enumerate(yields):
                for j, item in enumerate(row):
                    print(
                        str(item).ljust(colwidths[j])
                        if j == 0
                        else str(item).rjust(colwidths[j] + 4),
                        end="" if j < len(row) - 1 else "\n",
                    )
                if i == len(self._store["stack"]):
                    print("-" * (sum(colwidths) + (len(colwidths) - 1) * 4))
        if path is not None:
            if path.endswith(".csv"):
                with open(path, "w") as out:
                    for row in yields:
                        out.write(";".join(row) + "\n")
            elif path.endswith((".tex", ".pdf")):
                latextable = []
                latextable.append("""\\begin{tabular}{lrlr}""")
                latextable.append("""\\toprule""")
                for i, row in enumerate(yields):
                    if i == 0:
                        latextable.append(
                            """{} \\\\""".format(
                                " & ".join(["""\\textbf{""" + e + """}""" for e in row])
                            )
                        )
                        latextable.append("""\\midrule""")
                    else:
                        latextable.append(
                            """{} \\\\""".format(
                                " & ".join(
                                    [
                                        r"$\pm$ " + e if j == 2 else e
                                        for j, e in enumerate(row)
                                    ]
                                )
                            )
                        )
                        if i == len(self._store["stack"]):
                            latextable.append("""\midrule""")
                latextable.append("""\\bottomrule""")
                latextable.append("""\\end{tabular}""")
                if path.endswith(".tex"):
                    with open(path, "w") as out:
                        for line in latextable:
                            out.write(line + "\n")
                if path.endswith(".pdf"):
                    if find_executable("pdflatex") is None:
                        logger.error(
                            "Cannot compile LaTeX yields table: Command "
                            "'pdflatex' not found!"
                        )
                    elif crop and find_executable("pdfcrop") is None:
                        logger.error(
                            "Cannot crop PDF yields table: Command 'pdfcrop' not found!"
                        )
                        crop = False
                    else:
                        TeX2PDF("\n".join(latextable), path, crop=crop)  # verbosity=2
            else:
                raise IOError(
                    "File extension '{}' not supported!".format(path.split(".")[-1])
                )
            logger.info("Created yields table: '{}'".format(path))

    def AddStackSortingProperty(self, property, reverse=False):
        r"""Append a :class:`.Histo1D` property to the hierarchical list sorting
        criteria.

        :param property: :class:`.Histo1D` property
        :type property: ``str``

        :param reverse: reverse sorting order (default: ``False``)
        :type reverse: ``bool``
        """
        if self._stacksorting is None:
            self._stacksorting = []
        self._stacksorting.append((property, reverse))

    def SetStackSorting(self, *args):
        r"""Define a hierarchical list sorting criteria (:class:`.Histo1D` properties).

        :param \*args: ``list`` or ``tuple`` of the format [property (``str``), reverse
            (``bool``)] (see :func:`Stack.AddStackSortingProperty`)
        :type \*args: ``list``, ``tuple``
        """
        for property, reverse in args:
            self.AddStackSortingProperty(property, reverse)

    def GetStackSorting(self):
        r"""Return the hierarchical list sorting criteria (:class:`.Histo1D`
        properties).

        :returntype: ``list``
        """
        return self._stacksorting

    def SetDrawOption(self, option):
        # For some reason a THStack must be drawn with "SAMESAME" in the drawoption...
        # For "LEGO" and "SURF" drawoption "SAME" must not be added and the pad should
        # best be initialized with the "drawframe" property set to False!
        self._drawoption = option
        if not any(opt in self._drawoption.upper() for opt in ["LEGO", "SURF"]):
            self._drawoption += "SAME"
        super(Stack, self).SetDrawOption(option)

    def GetDrawOption(self):
        # Return the drawoption
        return self._drawoption

    def SetDrawStackSum(self, boolean):
        r"""Define whether the stacksum should be drawn.

        :param boolean: if set to ``True`` the stacksum will be drawn, overlaying the
            stack
        :type boolean: ``bool``
        """
        self._drawstacksum = boolean

    def GetDrawStackSum(self):
        r"""Return whether the stacksum should be drawn.

        :returntype: ``bool``
        """
        return self._drawstacksum

    def Draw(self, drawoption=None):
        # Draw the stacked, unstacked and finally the stacksum histograms.
        if drawoption is not None:
            self.SetDrawOption(drawoption)
        super(Stack, self).Draw(self.GetDrawOption())
        for histo in self._store["nostack"]:
            histo.Draw(histo.GetDrawOption() + "SAME")
        if self._drawstacksum:
            self._stacksumhisto.Draw(self._stacksumhisto.GetDrawOption() + "SAME")


if __name__ == "__main__":

    from Text import Text

    filename = "../data/ds_data18.root"

    nbkgs = 6
    t = Text(0.0, 0.5, "MEEP", ndc=False, textcolor=ROOT.kRed)  # to be injected

    threshold = (
        [220]
        + [450]
        + [500 + i * (200.0 / nbkgs) for i in range(nbkgs - 1)]
        + [420, 470]
    )

    h = {}
    s = Stack()
    nbkgs += 1
    for i in range(1, 1 + nbkgs + 2, 1):
        h[i] = Histo1D("h{}".format(i), "Histogram {}".format(i), 20, 0.0, 400.0)
        h[i].Fill(
            filename,
            tree="DirectStau",
            varexp="MET",
            cuts="tau1Pt>{}".format(threshold[i - 1]),
        )
        if i > 1 and i <= nbkgs:
            s.Register(h[i], stack=True, template="background", fillcolor=i)
    s.Register(h[1], stack=False, template="data")
    s.Register(h[nbkgs + 1], stack=False, template="signal", linecolor="#ff8200")
    s.Register(h[nbkgs + 2], stack=False, template="signal", linecolor="#00c892")

    s.PrintYieldTable("tmp/table.pdf", mkdir=True)

    for j in range(4):
        s.Print(
            "test_stack_{}.pdf".format(j),
            contribution=j >= 1,
            ratio=j >= 2,
            sensitivity=j >= 3,
            # ymax=1e5,
            ymin=1e-1,
            logy=True,
            xtitle="E_{T}^{miss}",
            xunits="GeV",
            luminosity=139,
            stacksumtitle="SUM",
            **{k: v for k, v in {"inject1": t}.items() if j > 0}
        )
