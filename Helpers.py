#!/usr/bin/env python2

import ROOT

import os

import logging
from logger import logger


def ColorID(color):
    # Convert a hex color code into a TColor.
    if isinstance(color, str) or isinstance(color, unicode):
        return ROOT.TColor.GetColor(color)
    elif isinstance(color, ROOT.TColor) or isinstance(color, int) or color is None:
        return color
    else:
        raise TypeError


def CheckPath(mode="r"):
    # Decorator for functions and methods with a filepath as their first argument (not
    # counting 'self' etc.).

    assert(mode in ["r", "w"]) # read / write

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
                        logger.debug("Existing file '{}' will be overwritten".format(
                            filepath))
                    else: raise IOError("File already exists: '{}'".format(filepath))
            else:
                if mode == "r":
                    raise IOError("File does not exist: '{}'".format(filepath))
                dir = os.path.dirname(filepath)
                if not os.path.isdir(dir):
                    if mkdir:
                        os.makedirs(dir)
                        logger.info("Created directory '{}'".format(dir))
                    else:
                        raise IOError("Directory '{}' does not exist!".format(dir))
            return filepath

        def wrapper(*args, **kwargs):
            mkdir = kwargs.pop("mkdir", False)
            overwrite = kwargs.pop("overwrite", True)
            args = list(args)
            if args:
                if bool(func.__name__ in dir(args[0])):
                    if len(args) > 1: idx = 1
                else: idx = 0
                args[idx] = check(args[idx],
                    overwrite=overwrite,
                    mkdir=mkdir)
            return func(*args, **kwargs)

        return wrapper
    return decorator
