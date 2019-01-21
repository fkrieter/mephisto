import ROOT

"""Set ROOT to batch and ignore command line options"""
ROOT.gROOT.SetBatch()
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
