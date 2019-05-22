#!/usr/bin/env python2

import ROOT

import os
import uuid
import time

from logger import logger


def ColorID(color):
    # Convert a hex color code into a TColor.
    if isinstance(color, str) or isinstance(color, unicode):
        return ROOT.TColor.GetColor(color)
    elif isinstance(color, ROOT.TColor) or isinstance(color, int) or color is None:
        return color
    else:
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


def CheckPath(mode="r"):
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
                    idx = 0
                args[idx] = check(args[idx], overwrite=overwrite, mkdir=mkdir)
            return func(*args, **kwargs)

        return wrapper

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

        return wrapper

    return decorator


def timeit(method):
    # https://goo.gl/XmaqC7
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", method.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            logger.debug(
                "Executed {} in {:.2f} ms".format(method.__name__, (te - ts) * 1000)
            )
        return result

    return timed
