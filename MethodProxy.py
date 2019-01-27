#!/usr/bin/env python2

import os
import re
import json

import logging
from logger import logger

from Helpers import ColorID


class MethodProxy(object):

    def __init__(self):
        self._cache = {}
        self._templates = {}
        self._methods = []
        self._properties = []
        childcls = self.__class__
        # Consider this:
        # 1. There are some setters for which there is no corresponding getter.
        # 2. We don't want a proxy for getters (and their corresponding setters),
        #    which require an argument.
        # 3. For each getter there should be a setter.
        setter = [f for f in dir(childcls) if f.startswith("Set") \
            and callable(getattr(childcls, f))]
        getter = [f for f in dir(childcls) if f.startswith("Get") \
            and callable(getattr(childcls, f))]
        unwntd_getter = [f for f in getter if getattr(childcls, \
            f).func_code.co_argcount >= 2]
        self._methods += [f for f in setter if "Get{}".format(f[3:]) not in \
            unwntd_getter] + [f for f in getter if "Set{}".format(f[3:]) in setter \
            and f not in unwntd_getter]
        self._properties = sorted(set([f[3:].lower() for f in self._methods \
            if f[3:] != ""]))
        jsonpath = "templates/{}_templates.json".format(self.__class__.__name__)
        if os.path.exists(jsonpath):
            self._templates = json.load(open(jsonpath))
        # print self._methods

    def GetListOfProperties(self):
        return self._properties

    def PrintAvailableProperties(self):
        def chunks(l, n):
            # Yield successive n-sized chunks from l.
            # (https://stackoverflow.com/a/312464)
            for i in range(0, len(l), n):
                yield l[i:i + n]
        print self.__class__.__name__, "has the following properties:"
        for chunk in chunks(self._properties, 5):
            print " "*4 + "".join([format(p, '<20') for p in chunk])

    def CacheProperties(self):
        for getter in [g for g in self._methods if g.startswith("Get")]:
            property = getter[3:].lower()
            self._cache[property] = getattr(self, getter)()

    def DeclareProperty(self, property, args):
        if args is None:
            return
        if property == "template":
            if not isinstance(args, str):
                raise ValueError("Expected property '{}' to be of type 'str'!".format(
                    property))
            self.DeclareProperties(**self._templates[args])
        regex = re.compile("Set{}$".format(property), re.IGNORECASE)
        match = list(filter(regex.match, self._methods))
        if not match:
            raise KeyError("Unknown property '{}'!".format(property))
        elif len(match) > 1:
            raise KeyError("Ambigious property '{}'! Matched to '{}'".format(
                property, ', '.join(match)))
        if isinstance(args, tuple) or isinstance(args, list):
            if "color" in property.lower():
                args[0] = ColorID(args[0])
            try:
                return getattr(self, match[0])(*args)
            except TypeError:
                if logger.isEnabledFor(logging.DEBUG):
                    raise
                pass
        else:
            if "color" in property.lower():
                args = ColorID(args)
            try:
                return getattr(self, match[0])(args)
            except TypeError:
                if logger.isEnabledFor(logging.DEBUG):
                    raise
                pass

    def DeclareProperties(self, **kwargs):
        properties = {}
        templatename = kwargs.pop("template", None)
        if templatename:
            properties.update(self._templates[templatename])
        properties.update(kwargs)
        for property, args in properties.items():
            self.DeclareProperty(property, args)

    def ResetProperty(self, property):
        self.DeclareProperty(property, self._cache[property])

    def ResetProperties(self):
        for property, args in self._cache.items():
            self.DeclareProperty(property, args)


class UsingProperties(object):

    def __init__(self, object, **kwargs):
        self._object = object
        self._object.CacheProperties()
        self._tmpproperties = kwargs

    def __enter__(self):
        self._object.DeclareProperties(**self._tmpproperties)

    def __exit__(self, *args):
        self._object.ResetProperties()
