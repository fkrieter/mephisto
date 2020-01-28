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
    r"""Class for creating plots.

    Stores :class:`ROOT` objects like histograms and draws them in their specified
    :class:`.Pad` onto a :class:`.Canvas`.
    """

    def __init__(self, name=uuid4().hex[:8], **kwargs):
        r"""Initialize a plot.

        Create an instance of :class:`.Plot` with the specified **name**.

        :param name: name of the plot (default: random 8-digits HEX hash value)
        :type name: ``str``

        :param \**kwargs: :class:`.Plot` properties
        """
        MethodProxy.__init__(self)
        self._name = name
        self._npads = 1
        self._store = defaultdict(list)
        self._padproperties = defaultdict(dict)
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
        r"""Return the name of the plot object.

        :returntype: ``str``
        """
        return self._name

    def SetNPads(self, npads):
        r"""Set the number of :class:`Pad` s associated to the plot.

        This will also determine the size and layout of the underlying :class:`Canvas`.

        :param npads: number of pads (default: 1)
        :type npads: ``int``
        """
        self._npads = npads

    def GetNPads(self):
        r"""Return the number of :class:`Pad` s associated to the plot.

        :returntype: ``int``
        """
        return self._npads

    def AssertPadIndex(self, idx):
        # Check if the given pad index is valid.
        assert isinstance(idx, int)
        if idx >= self._npads:
            raise IndexError(
                "Cannot register object to pad '{}': Plot was initialized with "
                "'npads={}' (default: 1)".format(idx, self._npads)
            )

    @MephistofyObject()
    def Register(self, object, pad=0, **kwargs):
        r"""Register a :class:`ROOT` object to the plot.

        The associated :class:`.Pad` is defined by **pad**. Properties of the **object**
        and the associated :class:`.Pad` can be changed via keyword arguments.

        :param object: *drawable* :class:`ROOT` object to be registered to the plot,
            e.g. ``Histo1D``, ``TH1D``, ``Histo2D``, ``TH2D``, ``Stack``, ...
        :type object: ``ROOT.TObject``

        :param pad: index of the target pad (default: 0)
        :type pad: ``int``

        :param \**kwargs: **object**, :class:`.Pad` properties
        """
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

    def SetStyle(self, style):
        # Define the global plotting style.
        self._style = style
        ROOT.gROOT.SetStyle(style)
        if style == "ATLAS":
            ROOT.gStyle.SetErrorX(0.5)

    def GetStyle(self):
        # Return the global plotting style.
        return self._style

    @CheckPath(mode="w")
    def Print(self, path, **kwargs):
        r"""Print the plot to a file.

        Creates a :class:`.Canvas` and draws all registered objects into their
        associated :class:`Pad`. The canvas is saved as a PDF/PNG/... file with the
        absolute path defined by **path**. If a file with the same name already exists
        it will be overwritten (can be changed  with the **overwrite** keyword
        argument). If **mkdir** is set to ``True`` (default: ``False``) directories in
        **path** with do not yet exist will be created automatically.

        The properties of the of the plot and canvas can be configured via their
        respective properties passed as keyword arguments.

        :param path: path of the output file (must end with '.pdf', '.png', ...)
        :type path: ``str``

        :param \**kwargs: :class:`.Plot` and :class:`.Canvas` properties + additional
            properties (see below)

        Keyword Arguments:

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
        for idx, injections in {
            int(k[6:]) if len(k) > 6 else 0: kwargs.pop(k)
            for k in dict(kwargs.items())
            if k.startswith("inject")
        }.items():
            if not isinstance(injections, list):
                injections = [injections]
            self.Inject(idx, *injections)
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
        if os.path.isfile(path):
            logger.info("Created plot: '{}'".format(path))
        canvas.Delete()

    def Inject(self, pad=0, *args):
        r"""Inject a (list of) *drawable* object(s) to the pad with index **pad**.

        Object properties can be specified by passing instead a ``tuple`` of the format
        :code:`(obj, props)` where :code:`props` is a ``dict`` holding the object
        properties.

        :param pad: index of the target pad (default: 0)
        :type pad: ``int``

        :param \*args: *drawable* :class:`ROOT` object or ``tuple`` of the format
            :code:`(obj, props)` where :code:`props` is a ``dict`` holding the object
            properties
        :type \*args: ``tuple``, ``ROOT.TObject``
        """
        self.AssertPadIndex(pad)
        for arg in args:
            if isinstance(object, tuple):
                obj, props = object
                if not isinstance(props, dict):
                    raise TypeError(
                        "Injection failed: {} is not a valid format!".format(arg)
                    )
                self.Register(obj, pad, **props)
            else:
                self.Register(arg, pad)

    def SetLabel(self, label):
        r"""Set the plot label.

        :param label: plot label (default: 'ATLAS')
        :type label: ``str``
        """
        self._label = label

    def GetLabel(self):
        r"""Return the plot label.

        :returntype: ``str``
        """
        return self._label

    def SetState(self, state):
        r"""Set the plot state.

        :param label: plot state (default: 'Work In Progress')
        :type label: ``str``
        """
        self._state = state

    def GetState(self):
        r"""Return the plot state.

        :returntype: ``str``
        """
        return self._state

    def SetCME(self, cme):
        r"""Set the value of the center-of-mass energy.

        :param label: center-of-mass energy in TeV
        :type label: ``int``, ``str``
        """
        self._cme = int(cme)

    def GetCME(self):
        r"""Return the center-of-mass energy.

        :returntype: ``int``
        """
        return self._cme

    def SetLuminosity(self, lumi):
        r"""Set the value of the integrated luminosity.

        :param label: integrated luminosity in :math:`\text{fb}^{-1}`
        :type label: ``float``, ``str``
        """
        self._lumi = float(lumi)

    def GetLuminosity(self):
        r"""Return the integrated luminosity.

        :returntype: ``float``
        """
        return self._lumi

    def GetPadHeight(self, pad=0):
        # Return the height of the pad with given index.
        self.AssertPadIndex(pad)
        x1, y1, x2, y2 = self._padproperties[pad]["padposition"]
        return y2 - y1

    def GetPadWidth(self, pad=0):
        # Return the width of the pad with given index.
        self.AssertPadIndex(pad)
        x1, y1, x2, y2 = self._padproperties[pad]["padposition"]
        return x2 - x1

    def AddPlotDecorations(self):
        # Register the plot label, state, CME and lumi to the main pad (0).
        # TODO: Maybe make the ref points a property?
        refx = (
            self._padproperties[0]["padposition"][0]  # x1
            + self._padproperties[0]["leftmargin"]
            + 0.04
        )
        refy = (
            self._padproperties[0]["padposition"][3]  # y2
            - self._padproperties[0]["topmargin"]
            - 0.09
        )
        label = None
        if self._label:
            label = Text(refx, refy, "{} ".format(self._label), textfont=73)
            self.Register(label)
            if not label.GetTitle() == "ATLAS ":
                label_xsize = label.GetXsize()
                label_ysize = label.GetYsize()
            else:
                label_xsize = 0.125
                label_ysize = 0.037
        if self._state:
            if label:
                state = Text(label.GetX() + label_xsize, label.GetY(), self._state)
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
                    label.GetY() - 1.75 * label_ysize,
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
