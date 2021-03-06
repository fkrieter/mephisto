#!/usr/bin/env python2

import ROOT

import os
import re
import uuid
import time
import inspect

from math import sqrt, log
from subprocess import Popen, PIPE, STDOUT

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, "wb")

from math import log10

from logger import logger

# Don't decorate functions when building the documentation
# https://stackoverflow.com/a/22023805/10986034
IS_SPHINX_BUILD = bool(os.getenv("SPHINX_BUILD"))


def ColorID(color):
    # Convert a hex color code into a TColor.
    if isinstance(color, (str, unicode)):
        return ROOT.TColor.GetColor(color)
    elif isinstance(color, (ROOT.TColor, int, long)) or color is None:
        return color
    else:
        logger.error("Color '{}' is of invalid type '{}'!".format(color, type(color)))
        raise TypeError


def DissectProperties(propdict, listofobj):
    # Disentangles a dictionary of properties and associates the entries to the given
    # list of objects or classes (must inherit from MethodProxy) in a consecutive
    # manner. The key 'template' will be associated to the first entry in the list.
    properties = {}
    for obj in listofobj:
        if isinstance(obj, dict):
            if len(obj.keys()) != 1:
                raise KeyError(
                    "Expected dictionary with exactly 1 key ({} given)".format(
                        len(obj.keys())
                    )
                )
            key = obj.keys()[0]
            values = obj[key]
            properties[key] = {
                k: propdict.pop(k) for k, v in propdict.items() if k in values
            }
            continue
        clsname = obj.GetClassName()
        clsprops = obj.GetListOfProperties()
        clsprops += ["template"]
        properties[clsname] = {
            k: propdict.pop(k) for k, v in propdict.items() if k in clsprops
        }
    if propdict:
        logger.error(
            "Unknown keyword argument(s) '{}'".format(", ".join(propdict.keys()))
        )
        raise KeyError
    return properties


def CheckPath(mode="r", clean=True):
    # Decorator for functions and methods with a filepath as their first argument (not
    # counting 'self' etc.).

    assert mode in ["r", "w"]  # read / write

    def decorator(func):
        def check(filepath, overwrite=True, mkdir=False):
            # If the file exists and overwrite=False raise an exception.
            # If file does not exist check if all directories in the given path exist.
            # If not raise an exception or if mkdir=True create them recursively.
            # Also formats relative paths or one with env vars as an absolute path.
            filepath = os.path.abspath(os.path.expandvars(filepath))
            if mode == "w"  and clean:
                filepath = clean_str(
                    filepath, remove="""~!@#$%^&*()+=<>\[\]{},;`'"\|"""
                )
            if os.path.isfile(filepath):
                if mode == "w":
                    if overwrite:
                        logger.debug(
                            "Existing file '{}' will be overwritten".format(filepath)
                        )
                    else:
                        logger.error("File already exists: '{}'".format(filepath))
                        raise IOError
            else:
                if mode == "r":
                    logger.error("File does not exist: '{}'".format(filepath))
                    raise IOError
                dir = os.path.dirname(filepath)
                if not os.path.isdir(dir):
                    if mkdir:
                        os.makedirs(dir)
                        logger.info("Created directory '{}'".format(dir))
                    else:
                        logger.error("Directory '{}' does not exist!".format(dir))
                        raise IOError
            return filepath

        def wrapper(*args, **kwargs):
            mkdir = kwargs.pop("mkdir", False)
            overwrite = kwargs.pop("overwrite", True)
            args = list(args)
            if args:
                if bool(func.__name__ in dir(args[0])):
                    if len(args) > 1:
                        idx = 1
                    else:
                        return func(*args, **kwargs)
                else:
                    idx = 0
                args[idx] = check(args[idx], overwrite=overwrite, mkdir=mkdir)
            return func(*args, **kwargs)

        return func if IS_SPHINX_BUILD else wrapper

    return decorator


def MergeDicts(*dicts):
    # Merge an arbitrary number of dictionaries. If multiple dictionaries contain the
    # same key, the last one in the list will define the final value in the output.
    merged = dicts[0].copy()
    for d in dicts[1:]:
        merged.update(d)
    return merged


def MephistofyObject(copy=False):
    # Decorator for functions and methods with a ROOT (or MEPHISTO) object as their
    # first argument (not counting 'self' etc.).

    assert isinstance(copy, bool)

    def decorator(func):
        def mephistofy(object):
            # If the object class inherits from MethodProxy return the original object
            # unless copy=True then continue. If not substitute the object with an
            # instance of the corresponding MEPHISTO class - imported here to avoid
            # circular imports - by calling the copy constructor.
            from Text import Text
            from Stack import Stack
            from Graph import Graph
            from Histo1D import Histo1D
            from Histo2D import Histo2D

            def lookupbases(cls):
                bases = list(cls.__bases__)
                for base in bases:
                    bases.extend(lookupbases(base))
                return bases

            clsname = object.__class__.__name__
            if "MethodProxy" in [
                basecls.__name__ for basecls in lookupbases(object.__class__)
            ]:
                if not copy:
                    return object
            suffix = "mephistofied" if not copy else "copy"
            if object.InheritsFrom("TH2"):
                return Histo2D("{}_{}".format(object.GetName(), suffix), object)
            elif object.InheritsFrom("TH1"):
                return Histo1D("{}_{}".format(object.GetName(), suffix), object)
            elif object.InheritsFrom("THStack"):
                return Stack("{}_{}".format(object.GetName(), suffix), object)
            elif object.InheritsFrom("TGraph"):
                return Graph("{}_{}".format(object.GetName(), suffix), object)
            elif object.InheritsFrom("TText") or object.InheritsFrom("TLatex"):
                return Text(object)
            raise NotImplementedError

        def wrapper(*args, **kwargs):
            mkdir = kwargs.pop("mkdir", False)
            overwrite = kwargs.pop("overwrite", True)
            args = list(args)
            if args:
                if bool(func.__name__ in dir(args[0])):
                    if len(args) > 1:
                        idx = 1
                else:
                    idx = 0
                args[idx] = mephistofy(args[idx])
            return func(*args, **kwargs)

        return func if IS_SPHINX_BUILD else wrapper

    return decorator


def timeit(func):
    # https://goo.gl/XmaqC7
    def timed(*args, **kw):
        ts = time.time()
        result = func(*args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", func.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            try:
                is_method = inspect.getargspec(func)[0][0] == "self"
            except:
                is_method = False

            if is_method:
                funcname = "{}.{}.{}".format(
                    func.__module__, args[0].__class__.__name__, func.__name__
                )
            else:
                funcname = "{}.{}".format(func.__module__, func.__name__)
            logger.debug("Executed {} in {:.2f} ms".format(funcname, (te - ts) * 1000))
        return result

    return func if IS_SPHINX_BUILD else timed


def IsInherited(cls, method):
    # https://stackoverflow.com/a/7752095/10986034
    if method not in cls.__dict__:  # Not defined in cls -> inherited
        return True
    # elif hasattr(super(cls), method):  # Present in parent -> overloaded
    #     return False
    else:  # Not present in parent -> newly defined
        return False


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    # https://stackoverflow.com/a/33024979/10986034
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def roundsig(x, nsig=1, **kwargs):
    # Round to 'nsig' significant digits. If decimals=True 'x' will be rounded to 'nsig'
    # decimals instead.
    decimals = int(log10(abs(x)))
    if kwargs.get("decimals", False):
        decimals = 0 if decimals > 0 else decimals
    return round(x, nsig - decimals)


def clean_str(string, **kwargs):
    # Remove unwanted characters from a string. By default almost all special characters
    # are removed. Special replacements can be defined with the "special" keyword as
    # a dictionary The default replacement is given by the "substitute" keyword.
    remove = kwargs.pop("remove", """~!@#$%^&*()+=<>\[\]{}:,;`'"/\|""")
    substitute = kwargs.pop("substitute", "")
    special = kwargs.pop("special", {".": "p"})
    for char, sub in special.items():
        if not char in remove:
            continue
        remove = remove.replace(char, "")
        string = string.replace(char, sub)
    if not remove:
        return string
    return re.sub("[{}]".format(remove), "", string)


def TeX2PDF(content, path, **kwargs):
    __filedir__ = os.path.dirname(os.path.abspath(__file__))
    verbosity = kwargs.get("vebosity", 0)
    assert verbosity in range(3)
    crop = kwargs.get("crop", True)
    header = (
        r"\documentclass[11pt]{article}" + "\n"
        r"\input{" + __filedir__ + r"/preamble}" + "\n"
        r"\begin{document}" + "\n"
        r"\pagenumbering{gobble}" + "\n"
    )
    tmpname = "tmp_{}".format(uuid.uuid4().hex[:8])
    outdir = os.path.dirname(path)
    tmptexfile = os.path.join("{}.tex".format(tmpname))
    # Write TeX file
    with open(tmptexfile, "w") as tmp:
        tmp.write(header)
        tmp.write(content)
        tmp.write("\n" + r"\end{document}")
    # Compile TeX file
    logger.debug("Compiling TeX file '{}'...".format(tmptexfile))
    cmd = [
        "pdflatex",
        "-interaction",
        "nonstopmode" if verbosity == 2 else "batchmode",
        # "-output-directory={}".format(outdir),
        tmptexfile,
    ]
    procoptions = dict(stdout=DEVNULL) if verbosity == 0 else {}
    proc = Popen(cmd, **procoptions)
    proc.communicate()
    retcode = proc.returncode
    if not retcode == 0:
        if retcode == 1:
            logger.warning(
                "Non-critical error (code {}) executing command: '{}'. Will keep going "
                "anyway...".format(retcode, " ".join(cmd))
            )
        else:
            logger.error(
                "Error {} executing command: '{}'".format(retcode, " ".join(cmd))
            )
            raise ValueError
    else:
        logger.debug("Successfully compiled '{}'!".format(tmptexfile))
    for ext in ["tex", "log", "aux"]:
        os.unlink("{}.{}".format(tmpname, ext))
    # Crop PDF file
    if crop:
        logger.debug("Cropping PDF file '{}.pdf'...".format(tmpname))
        cmd = ["pdfcrop", "--margins", "10", "{}.pdf".format(tmpname), path]
        proc = Popen(cmd, **procoptions)
        proc.communicate()
        retcode = proc.returncode
        if not retcode == 0:
            logger.error(
                "Error {} executing command: '{}'".format(retcode, " ".join(cmd))
            )
            raise ValueError
        else:
            os.unlink(os.path.join("{}.pdf".format(tmpname)))
            logger.debug("Successfully cropped PDF file '{}.pdf'!".format(tmpname))
    logger.debug("PDF file has been created: '{}'".format(path))


def SplitCutExpr(cutexpr):
    assert isinstance(cutexpr, str)
    rgx = (
        "(?P<varexp>[A-Za-z0-9\_()+\-*\/^%]+)(?P<comparator>(>=|<=|==|>|<))"
        "(?P<value>[+-]?\d*\.?\d*$)"
    )
    match = re.match(rgx, cutexpr)
    if match is not None:
        return match.groupdict()
    raise ValueError("Argument '{}' is not a valid cut expression!".format(cutexpr))


class AsymptoticFormulae(object):
    """A collection of useful asymptotic formulae for hypothesis tests."""

    @staticmethod
    def BinomialExpZ(s, b, db):
        # Discovery significance
        return ROOT.RooStats.NumberCountingUtils.BinomialExpZ(s, b, db)

    @staticmethod
    def BinomialExpP(s, b, db):
        # p_b value
        return ROOT.RooStats.NumberCountingUtils.BinomialExpP(s, b, db)

    @staticmethod
    def BinomialExpCLs(s, b, db):
        # Quite "experimental" way of computing CLs. Gives bad results for b < 1 and
        # otherwise seems to slightly underestimate the exclusion (overestimate CLs).
        # CL_s = p_s+b / 1 - p_b
        psb = 1.0 - AsymptoticFormulae.BinomialExpP(-s, s + b, db)
        return psb / (1.0 - AsymptoticFormulae.BinomialExpP(0, b, db))

    @staticmethod
    def AsimovExpZ(s, b, db):
        # [1] http://www.pp.rhul.ac.uk/~cowan/stat/medsig/medsigNote.pdf (Eq. 20)
        s = float(s)
        b = float(b)
        db *= b
        try:
            return sqrt(
                2
                * (
                    (s + b)
                    * log(((s + b) * (b + db ** 2)) / (b ** 2 + (s + b) * db ** 2))
                    - ((b ** 2 / db ** 2) * log(1 + s * db ** 2 / (b * (b + db ** 2))))
                )
            )
        except ValueError:
            return 0

    @staticmethod
    def AsimovExpCLs(s, b, db):
        # [1] https://arxiv.org/pdf/1007.1727.pdf (Sec. 5.1)
        logLH = lambda n, m, mu, s, b, tau: n * log(mu * s + b) + (
            m * log(tau * b) - mu * s - (1 + tau) * b
        )

        db *= b

        mu = 1
        tau = b / (db ** 2)

        # Asimov dataset for mu = 0 (expected exclusion)
        n = b
        m = tau * b

        # Maximum-likelihood estimators from [1]
        muhat = (n - m / tau) / s
        bhat = m / tau
        bhathat = (
            (n + m - (1 + tau) * mu * s)
            + sqrt((n + m - (1 + tau) * mu * s) ** 2 + 4 * (1 + tau) * m * mu * s)
        ) / (2 * (1 + tau))

        cond_logLH = logLH(n, m, mu, s, bhathat, tau)
        uncond_logLH = logLH(n, m, muhat, s, bhat, tau)

        # Compute the exclusion significance and transform it into p_s+b.
        # Z_excl = sqrt(teststat), teststat = - 2 ln(condLH / uncondLH)
        # In the asymptotic limit, the expected p_b = 0.5.
        # CL_s = p_s+b / 1 - p_b
        return 2.0 * ROOT.RooStats.SignificanceToPValue(
            sqrt(-2.0 * (cond_logLH - uncond_logLH))
        )


try:
    # https://gitlab.cern.ch/nihartma/meme
    import meme

    def cache(**options):
        options.setdefault("ttl", 7 * 24 * 60 * 60)  # 7 days lifetime
        options.setdefault("cacheDir", "/dev/shm/mephisto/")  # use shared memory

        def decorator(func):
            meme_cache = meme.cache(**options)
            return func if IS_SPHINX_BUILD else meme_cache(func)

        return decorator


except ImportError:
    logger.info("Couldn't find meme module. Caching is not available.")
    # Define a dummy:
    def cache(**options):
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return func if IS_SPHINX_BUILD else wrapper

        return decorator
