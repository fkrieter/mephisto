#!/usr/bin/env python2.7

from __future__ import print_function

import ROOT

from Stack import Stack


class ContributionPlot(Stack):
    r"""Class for a normalized stack of 1-dimensional.

    +-------------------------------------------------------------------------------+
    | Inherits from :class:`.Stack` which inherits from :class:`ROOT.THStack`, see  |
    | official `documentation <https://root.cern.ch/doc/master/classTHStack.html>`_ |
    | as well!                                                                      |
    +-------------------------------------------------------------------------------+

    Has the same features as :class:`.Stack` but only draws all stacked histograms
    normalized with respect to their sum (**stacksum**).
    """

    def __init__(self, *args, **kwargs):
        r"""Initialize a stack of 1-dimensional histograms.

        Create an instance of :class:`.ContributionPlot` from a given ``Stack`` or list
        of histograms (**\*args**).

        :param \*args: see below

        :param \**kwargs: :class:`.ContributionPlot` properties

        :Arguments:
            Depending on the number of arguments there are two ways to initialize a
            :class:`.ContributionPlot` object\:

            * *one* argument of type ``Stack`` or ``THStack``\:

                #. **stack** (``Stack``, ``THStack``) -- copy all stacked histograms
                   from the **stack**

            * *multiple* arguments of type ``Histo1D`` or ``TH1D``\:

                #. **\*args** (``Stack``, ``THStack``) -- register a list of histograms
                   to a new stack
        """
        self._loadTemplates()
        kwargs.setdefault("template", "common")
        name = "{}_ContributionPlotStack".format(args[0].GetName())
        super(ContributionPlot, self).__init__(name)
        if len(args) == 1 and args[0].InheritsFrom("THStack"):
            for histo in args[0].GetHists():
                self.Register(histo, stack=True)
        else:
            for histo in args:
                assert histo.InheritsFrom("TH1")
                self.Register(histo, stack=True)
        self.SortStack()  # before normalization!
        for bn in range(1, self._stacksumhisto.GetNbinsX() + 1, 1):
            for histo in self._store["stack"]:
                try:
                    histo.SetBinContent(
                        bn,
                        histo.GetBinContent(bn) / self._stacksumhisto.GetBinContent(bn),
                    )
                except ZeroDivisionError:
                    histo.SetBinContent(bn, 0)
            self._stacksumhisto.SetBinContent(bn, 1.0)
        self.DeclareProperties(**kwargs)
        self.BuildStack(sort=False)


if __name__ == "__main__":

    from Plot import Plot
    from Histo1D import Histo1D
    from IOManager import IOManager

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
    s.Register(h3, stack=True, template="background", fillcolor=ROOT.kRed)

    c = ContributionPlot(s)

    # p1 = Plot(npads=1)
    # p1.Register(c, 0, logy=False, ymax=1)
    # p1.Print("contributionplot_test.pdf")

    c.Print("contributionplot_test.pdf", logy=False, ymax=1)
