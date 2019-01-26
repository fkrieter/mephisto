#!/usr/bin/env python2

import ROOT

import logging
from logger import logger

def ColorID(color):
    # Convert a hex color code into a TColor.
    if isinstance(color, str) or isinstance(color, unicode):
        return ROOT.TColor.GetColor(color)
    elif isinstance(color, ROOT.TColor) or isinstance(color, int):
        return color
    else:
        raise TypeError
