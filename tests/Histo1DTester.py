#!/usr/bin/env python 2.7

from __future__ import print_function

import ROOT

import os
import uuid
import unittest

from mephisto import Histo1D


class Histo1DTester(unittest.TestCase):
    def Fill(self, path, **kwargs):
        self.histo = Histo1D(uuid.uuid4().hex[:16], "", 40, 0.0, 40.0)
        self.histo.Fill(path, **kwargs)
        self.assertIsNotNone(self.histo)
