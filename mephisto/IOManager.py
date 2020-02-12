#!/usr/bin/env python2.7

import os
import re
import uuid

import ROOT

from logger import logger
from Helpers import CheckPath, timeit, cache

import root_numpy as rnp

import numpy as np
from array import array


ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gErrorIgnoreLevel = 2000


class IOManager(object):
    r"""Static class providing easy-to-use methods for common :py:mod:`ROOT` I/O
    operations.

    Can be used to read from and write to :py:mod:`ROOT` files. Multiple histograms from
    one tree can be filled simultaneously using the :class:`.Factory` subclass.
    """

    @staticmethod
    @CheckPath(mode="w")
    def CreateTestSample(path, **kwargs):
        r"""Creates a :py:mod:`ROOT` file with toy data to be used for tests.

        The output file contains one tree with **nevents** number of entries represented
        by `nbranches` branches. Random numbers for each branch are drawn according to a
        chisquare distribution with a mean indicated by the branch index. The name of
        the output tree is given by **tree** and the branches are of the form
        'branch_1', 'branch_2', ...

        Numbers are generated using the :class:`numpy.random` module and the output file
        is filled using the :func:`root_numpy.array2root` method.

        If a file with the same name already exists it will be overwritten (can be
        changed  with the **overwrite** keyword argument). If **mkdir** is set to
        ``True`` (default: ``False``) directories in **path** with do not yet exist will
        be created automatically.

        :param path: path of output :py:mod:`ROOT` file
        :type path: ``str``

        :param \**kwargs: see below

        :Keyword Arguments:

            * **nevents** (``int``) -- number of events in the output tree (default:
              10000)

            * **nbranches** (``int``) -- number of branches (default: 10)

            * **tree** (``int``) -- name of the output tree (default: 'tree')

            * **overwrite** (``bool``) -- overwrite an existing file located at **path**
              (default: ``True``)

            * **mkdir** (``bool``) -- create non-existing directories in **path**
              (default: ``False``)
        """
        basedir = os.path.abspath(path)
        if not basedir:
            logger.error("Directory '{}' does not exist!".format(basedir))
            raise IOError("Path not found!")
        nevents = int(kwargs.get("nevents", 1e4))
        nbranches = int(kwargs.get("nbranches", 10))
        treename = kwargs.get("tree", "tree")
        array = np.core.records.fromarrays(
            np.transpose(
                np.random.chisquare(
                    range(1, nbranches + 1, 1), size=(nevents, nbranches)
                )
            ),
            names=",".join(["branch_{}".format(i + 1) for i in range(nbranches)]),
        )
        rnp.array2root(array, path, treename=treename, mode="recreate")
        if os.path.isfile(path):
            logger.info("Created '{}'.".format(path))

    @staticmethod
    def FillHistogram(histo, infile, **kwargs):
        r"""Fill a given histograms with events from a tree.

        The given histogram will be filled with values for the **varexp** for all events
        assing the **cuts** and weighted by **weight**. Via the **append** option one
        can decide whether the given histogram should be overwritten or if the new
        entries should be appended to its existing content. Basis for the input is the
        specified **tree** of the **infile**.

        The histogram is filled using :py:mod:`ROOT`'s ``TTree::Project`` method.

        :param histo: histogram object to be filled
        :type histo: ``ROOT.TH1D``, ``ROOT.TH2D``

        :param infile: path to the input :py:mod:`ROOT` file
        :type infile: ``str``

        :param \**kwargs: see below

        :Keyword Arguments:

            * **tree** (``str``) -- name of the input tree

            * **varexp** (``str``) -- name of the branch to be plotted (format: 'x' or
              'x:y')

            * **cuts** (``str``, ``list``, ``tuple``) -- string or list of strings of
              boolean expressions, the latter will default to a logical *AND* of all
              items (default: '1')

            * **weight** (``str``) -- number or name of the branch which will be applied
              as a weight (default: '1')

            * **append** (``bool``) -- append entries to the specified **histo** instead
              of overwriting it (default: ``False``)
        """
        append = kwargs.pop("append", False)
        kwargs.update(IOManager._getBinning(histo))
        varexp = kwargs.get("varexp")
        histoname = histo.GetName()
        histotitle = histo.GetTitle()
        histoclass = histo.ClassName()
        if not ":" in varexp:
            assert histoclass.startswith("TH1")
        elif len(varexp.split(":")) == 2:
            assert histoclass.startswith("TH2")
        else:
            raise NotImplementedError
        htmp = IOManager.GetHistogram(infile, **kwargs)
        if append:
            histo.Add(htmp)
        else:
            htmp.Copy(histo)
        del htmp
        histo.SetName(histoname)
        histo.SetTitle(histotitle)

    @staticmethod
    def _convertBinning(unformatted_binning, **kwargs):
        # Converts a binning dict or tuple/list into a "friendly" dict or list:
        # New binning will be a list of bin low-edges.
        csv_format = kwargs.get("csv", False)
        if unformatted_binning is None:
            return None
        elif isinstance(unformatted_binning, dict):
            formatted_binning_dict = {}
            for label, binning in unformatted_binning.items():
                formatted_binning_dict[label] = IOManager._convertBinning(
                    binning, **kwargs
                )
            return formatted_binning_dict
        elif isinstance(unformatted_binning, tuple):
            nbins, minval, maxval = unformatted_binning
            assert isinstance(nbins, int)
            minval = float(minval)
            maxval = float(maxval)
            step = (maxval - minval) / nbins
            formatted_binning = [minval + (i * step) for i in range(nbins + 1)]
        elif isinstance(unformatted_binning, list):
            formatted_binning = sorted(unformatted_binning)
        else:
            raise TypeError
        if csv_format:
            return ",".join([str(b) for b in formatted_binning])
        return formatted_binning

    @staticmethod
    def _getBinning(histo):
        # Get binning (list of bin low-edges) of a histogram for all coordinates.
        binning = {}
        for coord in ["x", "y", "z"]:
            axis = getattr(histo, "Get{}axis".format(coord.capitalize()))()
            binning[coord + "binning"] = [
                float(axis.GetBinLowEdge(i)) for i in range(1, axis.GetNbins() + 2, 1)
            ]
        return binning

    @staticmethod
    @timeit
    def GetHistogram(infile, **kwargs):
        r"""Create a histograms filled with events from a tree.

        The created histogram will be filled with values for the **varexp** for all
        events passing the **cuts** and weighted by **weight**. Basis for the input is
        the specified **tree** of the **infile**. The name and title of the histogram
        can be set via **name** and **title**, respectively.

        The histogram is filled using :py:mod:`ROOT`'s :func:`TTree.Project` method.

        :param infile: path to the input :py:mod:`ROOT` file
        :type infile: str

        :param \**kwargs: see below

        :Keyword Arguments:

            * **name** (``str``) -- name of the returned histogram

            * **title** (``str``) -- title of the returned histogram

            * **tree** (``str``) -- name of the input tree

            * **varexp** (``str``) -- name of the branch to be plotted (format: 'x' or
              'x:y')

            * **cuts** (``str``, ``list``, ``tuple``) -- string or list of strings of
              boolean expressions, the latter will default to a logical *AND* of all
              items (default: '1')

            * **weight** (``str``) -- number or branch name to be applied as a weight
              (default: '1')

        :returntype: ``ROOT.TH1D``, ``ROOT.TH2D``
        """
        cuts = kwargs.get("cuts", [])
        if isinstance(cuts, (list, tuple)):
            if cuts:
                kwargs["cuts"] = (
                    "&&".join(["({})".format(cut) for cut in cuts]) if cuts else "1"
                )
        elif not isinstance(cuts, str):
            raise TypeError
        for key in ["xbinning", "ybinning", "zbinning"]:
            binning = kwargs.get(key)
            if binning is None:
                continue
            kwargs[key] = IOManager._convertBinning(binning, csv=True)
        return IOManager._getHistogram(infile, **kwargs)

    @staticmethod
    @CheckPath(mode="r")
    @cache()
    def _getHistogram(infile, **kwargs):
        # Returns a TH1D with the given parameters and fills it via TTree::Project.
        # Uses binning in CSV format for faster caching.
        name = kwargs.get("name", uuid.uuid1().hex[:8])
        title = kwargs.get("title", "")
        xbinning = array("d", [float(x) for x in kwargs.get("xbinning").split(",")])
        treename = kwargs.get("tree")
        varexp = kwargs.get("varexp")
        weight = kwargs.get("weight", "1")
        cuts = kwargs.get("cuts", "1")
        if not ":" in varexp:
            htmp = ROOT.TH1D(name, title, len(xbinning) - 1, xbinning)
        elif len(varexp.split(":")) == 2:
            ybinning = array("d", [float(y) for y in kwargs.get("ybinning").split(",")])
            htmp = ROOT.TH2D(
                name, title, len(xbinning) - 1, xbinning, len(ybinning) - 1, ybinning
            )
        else:
            raise NotImplementedError
        htmp.Sumw2()
        tfile = ROOT.TFile.Open(infile, "read")
        ttree = tfile.Get(treename)
        if not isinstance(ttree, ROOT.TTree):
            logger.error("Specified tree='{}' not found!".format(treename))
        ROOT.gROOT.cd()
        nevts = ttree.Project(name, varexp, "({})*({})".format(weight, cuts), "goff")
        htmp.SetDirectory(0)
        tfile.Close()
        if nevts < 0:
            logger.error(
                "Failed to project varexp='{}', cuts={}, weight='{}' onto "
                "histogram '{}'. Tree '{}' contains the following branches:\n{}".format(
                    varexp,
                    cuts,
                    weight,
                    name,
                    treename,
                    "'" + "', '".join(IOManager._getListOfBranches(ttree)) + "'",
                )
            )
            tfile.Close()
            raise TypeError("Variable compilation failed!")
        htmp.SetEntries(nevts)
        return htmp

    @staticmethod
    def _getListOfBranches(tree):
        # Returns the names of all branches of a given TTree.
        branches = []
        for branch in tree.GetListOfBranches():
            branches.append(branch.GetName())
        return branches

    class Factory(object):
        r"""Subclass for filling multiple histograms from one tree in just one go.

        Create an instance of :class:`.Factory` for some tree in a given :py:mod:`ROOT`
        file and register histograms with the desired options to it. All registered
        histograms will then be filled simultaneously by only looping once over the
        tree, resulting in a significant time saving compared to calling
        :func:`~IOManager.IOManager.FillHistogram` multiple times.
        """

        @CheckPath(mode="r")
        def __init__(self, path, tree):
            r"""Initialize the :class:`.Factory` for a given **tree** in a
            :py:mod:`ROOT` file located at **path**.

            :param infile: path to the input :py:mod:`ROOT` file
            :type infile: ``str``

            :param tree: name of the input tree
            :type infile: ``str``
            """
            self._filepath = path
            self._treename = tree
            self._store = []
            infile = ROOT.TFile.Open(path)
            intree = infile.Get(self._treename)
            if not intree:
                raise KeyError(
                    "File '{}' has no tree called '{}'".format(
                        self._filepath, self._treename
                    )
                )
            self._entries = intree.GetEntries()
            infile.Close()

        def Register(self, histo, **kwargs):
            r"""Register a histograms to the factory.

            The registered histogram will be filled with values for the **varexp**
            for all events passing the **cuts** and weighted by **weight** upon calling
            :func:`~IOManager.IOManager.Factory.Run`.

            :param histo: histogram object to be filled
            :type histo: ``ROOT.TH1D``, ``ROOT.TH2D``

            :param \**kwargs: see below

            :Keyword Arguments:

                * **varexp** (``str``) -- name of the branch to be plotted (format: 'x'
                  or 'x:y')

                * **cuts** (``str``, ``list``, ``tuple``) -- string or list of strings
                  of boolean expressions, the latter will default to a logical *AND* of
                  all items (default: '1')

                * **weight** (``str``) -- number or branch name to be applied as a
                  weight (default: '1')
            """
            varexp = kwargs.pop("varexp")
            cuts = kwargs.pop("cuts", [])
            weight = kwargs.pop("weight", "1")
            append = kwargs.pop("append", False)
            # Save metadata to Histo1D/2D:
            if histo.__class__.__name__ in ["Histo1D", "Histo1D"]:
                histo._varexp = varexp
                histo._cuts = cuts
                histo._weight = weight
            if isinstance(cuts, (list, tuple)):
                cutstring = (
                    "&&".join(["({})".format(cut) for cut in cuts]) if cuts else "1"
                )
            elif isinstance(cuts, str):
                cutstring = cuts
            else:
                raise TypeError
            options = {
                "varexp": varexp,
                "weight": weight,
                "cuts": cutstring,
                "append": append,
            }
            histoname = histo.GetName()
            histotitle = histo.GetTitle()
            histoclass = histo.ClassName()
            if not ":" in varexp:
                assert histoclass.startswith("TH1")
            elif len(varexp.split(":")) == 2:
                assert histoclass.startswith("TH2")
            else:
                raise NotImplementedError
            self._store.append((histo, options))

        @timeit
        def Run(self, batchsize=int(1e5)):
            r"""Fill all registered histograms.

            The histograms are filled using the :func:`root_numpy.root2array` method.

            :param batchsize: number of events to processed at once (default: 100000)
            :type batchsize: ``int``
            """
            branchexprs = set()
            for histo, options in self._store:
                branchexprs.update(options["varexp"].split(":"))
                branchexprs.add("({})*({})".format(options["weight"], options["cuts"]))
                if not options["append"]:
                    histo.Reset()
            for start in range(0, self._entries, batchsize):
                array = rnp.root2array(
                    self._filepath,
                    self._treename,
                    branches=branchexprs,
                    start=start,
                    stop=start + batchsize,
                )
                for histo, options in self._store:
                    if not ":" in options["varexp"]:
                        varexp = array[options["varexp"]]
                    else:
                        varexp = rnp.rec2array(array[options["varexp"].split(":")])
                    cuts = array["({})*({})".format(options["weight"], options["cuts"])]
                    mask = np.where(cuts != 0)
                    rnp.fill_hist(histo, varexp[mask], weights=cuts[mask])
            for histo, options in self._store:
                if histo.GetEntries() == 0:
                    logger.warning(
                        "No events have been extracted for tree '{}' in file '{}'"
                        "using varexp='{}', cuts='{}', weight='{}'!".format(
                            self._treename,
                            self._filepath,
                            options["varexp"],
                            options["cuts"],
                            options["weight"],
                        )
                    )
            logger.info(
                "Filled {} histograms using tree '{}' in file '{}'.".format(
                    len(self._store), self._treename, self._filepath
                )
            )


def main():

    if not os.path.exists("../data"):
        os.mkdir("../data")
    testfile = "../data/test.root"
    IOManager.CreateTestSample(testfile)

    histo = ROOT.TH1D("histo_branch_1", "", 200, 0.0, 10.0)
    histo.Sumw2()
    IOManager.FillHistogram(
        histo,
        testfile,
        tree="tree",
        varexp="branch_5",
        cuts=["branch_1>0.1", "branch_2>0.25"],
    )
    canvas = ROOT.TCanvas()
    canvas.cd()
    histo.Draw("HIST")
    canvas.SaveAs("test.pdf")

    h = {}
    f = IOManager.Factory(testfile, "tree")
    for i in range(1, 11, 1):
        h[i] = ROOT.TH1D("h{}".format(i), "", 200, 0.0, 20.0)
        f.Register(h[i], varexp="branch_{}".format(i))
    f.Run()


if __name__ == "__main__":
    main()
