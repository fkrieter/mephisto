#!/usr/bin/env python2.7

import os
import re
import uuid

import ROOT

from logger import logger
from Helpers import CheckPath

import root_numpy as rnp

import numpy as np
from array import array


ROOT.gROOT.SetBatch()
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gErrorIgnoreLevel = 2000


class iomanager(object):
    """Class for easy ROOT I/O.

    Can be used to read from and write to ROOT files. Multiple histograms from one tree
    can be created simultaneously using the factory subclass.
    """

    # Dictionary holding histograms and configs for factory
    _registered_histos = {}

    @staticmethod
    @CheckPath(mode="w")
    def create_test_sample(path, **kwargs):
        """Creates a ROOT file with toy data to be used for tests.

        The output file contains one tree with `nevents` number of entries represented
        by `nbranches` branches. Random numbers for each branch are drawn according to a
        chisquare distribution with a mean indicated by the branch index. The name of
        the output tree is given by `tree` and the branches are of the form 'branch_1',
        'branch_2', ...

        Numbers are drawn using numpy's random module and the output file is created
        using root_numpy's array2root function.

        :param path: path of output ROOT file
        :type path: str

        :param nevents: number of events in the output tree (default: 10000)
        :type nevents: int

        :param nbranches: number of branches (default 10)
        :type nbranches: int

        :param tree: name of the output tree (default 'tree')
        :type tree: str
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
    def fill_histo(histo, infile, **kwargs):
        """Fill a given histograms with events from a tree.

        The given histogram will be filled with values for the `varexp` for all events
        assing the `cuts` and weighted by `weight`. Via the `append` option one can
        decide whether the given histogram should be overwritten or if the new entries
        should be appended to its existing content. Basis for the input is the specified
        `tree` of the `infile`.

        The histogram is filled using ROOT's TTree::Project method.

        :param histo: histogram object to be filled
        :type histo: ROOT.TH1D, ROOT.TH2D

        :param infile: path to the input ROOT file
        :type infile: str

        :param tree: name of the input tree
        :type tree: str

        :param varexp: name of the branch to be plotted (format: 'x' or 'x:y')
        :type varexp: str

        :param cuts: string or list of strings of boolean expressions, the latter\
        will default to a logical AND of all items (default: '1')
        :type cuts: str, list

        :param weight: number or branch name to be applied as a weight (default: '1')
        :type weight: str

        :param append: append or overwrite entries to the specified `histo` (default:\
        False)
        :type append: bool
        """
        append = kwargs.pop("append", False)
        kwargs.update(iomanager._get_binning(histo))
        varexp = kwargs.get("varexp")
        histoname = histo.GetName()
        histotitle = histo.GetTitle()
        histoclass = histo.ClassName()
        if not ":" in varexp:
            assert histoclass.startswith("TH1")
        elif len(varexp.split(":") == 2):
            assert histoclass.startswith("TH2")
        else:
            raise NotImplementedError
        htmp = iomanager.get_histo(infile, **kwargs)
        if append:
            histo.Add(htmp)
        else:
            htmp.Copy(histo)
        del htmp
        histo.SetName(histoname)
        histo.SetTitle(histotitle)

    @staticmethod
    def _convert_binning(unformatted_binning, **kwargs):
        # Converts a binning dict or tuple/list into a "friendly" dict or list:
        # New binning will be a list of bin low-edges.
        csv_format = kwargs.get("csv", False)
        if unformatted_binning is None:
            return None
        elif isinstance(unformatted_binning, dict):
            formatted_binning_dict = {}
            for label, binning in unformatted_binning.items():
                formatted_binning_dict[label] = iomanager._convert_binning(
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
    def _get_binning(histo):
        # Get binning (list of bin low-edges) of a histogram for all coordinates.
        binning = {}
        for coord in ["x", "y", "z"]:
            axis = getattr(histo, "Get{}axis".format(coord.capitalize()))()
            binning[coord + "binning"] = [
                float(axis.GetBinLowEdge(i)) for i in range(1, axis.GetNbins() + 2, 1)
            ]
        return binning

    @staticmethod
    def get_histo(infile, **kwargs):
        """Create a histograms filled with events from a tree.

        The created histogram will be filled with values for the `varexp` for all events
        passing the `cuts` and weighted by `weight`. Basis for the input is the
        specified `tree` of the `infile`. The name and title of the histogram can be set
        via `name` and `title`, respectively.

        The histogram is filled using ROOT's TTree::Project method.

        :param infile: path to the input ROOT file
        :type infile: str

        :param name: name of the returned histogram
        :type name: str

        :param title: title of the returned histogram
        :type title: str

        :param tree: name of the input tree
        :type tree: str

        :param varexp: name of the branch to be plotted (format: 'x' or 'x:y')
        :type varexp: str

        :param cuts: string or list of strings of boolean expressions, the latter\
        will default to a logical AND of all items (default: '1')
        :type cuts: str, list

        :param weight: number or branch name to be applied as a weight (default: '1')
        :type weight: str

        :returntype: ROOT.TH1D, ROOT.TH2D
        """
        for binning in ["xbinning", "ybinning"]:
            kwargs[binning] = iomanager._convert_binning(kwargs.get(binning), csv=True)
        h = iomanager._get_histo(infile, **kwargs)
        return iomanager._get_histo(infile, **kwargs)

    @staticmethod
    @CheckPath(mode="r")
    def _get_histo(infile, **kwargs):
        # Returns a TH1D with the given parameters and fills it via TTree::Project.
        # Uses binning in CSV format for faster caching.
        name = kwargs.get("name", uuid.uuid1().hex[:8])
        title = kwargs.get("title", "")
        xbinning = array("d", [float(x) for x in kwargs.get("xbinning").split(",")])
        treename = kwargs.get("tree")
        varexp = kwargs.get("varexp")
        weight = kwargs.get("weight", "1")
        cuts = kwargs.get("cuts", "1")
        if isinstance(cuts, list):
            cutstr = "&&".join(["({})".format(cut) for cut in cuts])
        elif isinstance(cuts, str):
            cutstr = cuts
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
        nevts = ttree.Project(name, varexp, "({})*({})".format(weight, cutstr), "goff")
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
                    "'" + "', '".join(iomanager._get_list_of_branches(ttree)) + "'",
                )
            )
            tfile.Close()
            raise TypeError("Variable compilation failed!")
        htmp.SetEntries(nevts)
        return htmp

    @staticmethod
    def _get_list_of_branches(tree):
        # Returns the names of all branches of a given TTree.
        branches = []
        for branch in tree.GetListOfBranches():
            branches.append(branch.GetName())
        return branches


def main():

    if not os.path.exists("../data"):
        os.mkdir("../data")
    testfile = "../data/test.root"
    iomanager.create_test_sample(testfile)

    histo = ROOT.TH1D("histo_branch_1", "", 200, 0.0, 10.0)
    histo.Sumw2()
    iomanager.fill_histo(
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


if __name__ == "__main__":
    main()
