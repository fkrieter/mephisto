import ROOT

"""Set ROOT to batch and ignore command line options"""
ROOT.gROOT.SetBatch(0)
ROOT.PyConfig.IgnoreCommandLineOptions = True

"""Set ROOT logging verbosity"""
ROOT.gErrorIgnoreLevel = 2000
# kUnset    =  -1
# kPrint    =   0
# kInfo     =   1000
# kWarning  =   2000
# kError    =   3000
# kBreak    =   4000
# kSysError =   5000
# kFatal    =   6000

from Pad import Pad
from Plot import Plot
from Line import Line
from Text import Text
from Stack import Stack
from Graph import Graph
from Arrow import Arrow
from logger import logger
from Canvas import Canvas
from Histo1D import Histo1D
from Histo2D import Histo2D
from N1Plotter import N1Plotter
from RatioPlot import RatioPlot
from IOManager import IOManager
from SensitivityScan import SensitivityScan
from ContributionPlot import ContributionPlot
