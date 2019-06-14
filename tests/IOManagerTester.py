#!/usr/bin/env python 2.7

import ROOT

import os
import unittest

from mephisto import IOManager


class IOManagerTester(unittest.TestCase):
    def CreateTestSample(self, path, **kwargs):
        nevents = kwargs.get("nevents")
        nbranches = kwargs.get("nbranches")
        IOManager.CreateTestSample(path, mkdir=True, overwrite=True, **kwargs)
        self.assertTrue(os.path.exists(path))
        tfile = ROOT.TFile.Open(path, "READ")
        self.assertTrue(tfile.IsOpen())
        self.assertTrue(tfile.IsFolder())
        self.assertEquals(len(tfile.GetListOfKeys()), 1)
        ttree = tfile.Get("tree")
        self.assertTrue(ttree)
        self.assertEquals(ttree.GetEntries(), nevents)
        branches = ttree.GetListOfBranches()
        self.assertEquals(len(branches), nbranches)
        for branch in branches:
            self.assertEquals(branch.GetEntries(), nevents)
