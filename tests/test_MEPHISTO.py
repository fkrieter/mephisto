#!/usr/bin/env python 2.7

import ROOT

import os

from mephisto.logger import logger

logger.setLevel(10)

from IOManagerTester import IOManagerTester
from Histo1DTester import Histo1DTester

__filedir__ = os.path.dirname(os.path.abspath(__file__))


class MEPHISTOTester(IOManagerTester, Histo1DTester):
    # Monolithic test: Module test are executed successively.
    # (see: https://stackoverflow.com/a/5387956/10986034)

    def setUp(self):
        self._datadir = os.path.join(__filedir__, "data")
        self._testsample = os.path.join(self._datadir, "test.root")
        self._tree = "tree"
        self._nbranches = 10

    def step1(self):
        """Create test sample"""
        nevents = 1e4
        self.CreateTestSample(
            self._testsample, nevents=nevents, nbranches=self._nbranches
        )

    def step2(self):
        """Fill histograms"""
        for i in range(self._nbranches):
            self.Fill(
                self._testsample, tree=self._tree, varexp="branch_{}".format(i + 1)
            )

    def retrieve_steps(self):
        for name in dir(self):  # dir() result is implicitly sorted
            if name.startswith("step"):
                yield int(name[4:]), getattr(self, name)

    def test_steps(self):
        for idx, step in self.retrieve_steps():
            try:
                logger.info("Step [{}] : Testing '{}'".format(idx, step.__doc__))
                step()
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))
            logger.info("Step [{}] : ==> SUCCESS!".format(idx))


if __name__ == "__main__":
    unittest.main()
