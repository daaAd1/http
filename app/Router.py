# -*- coding: utf-8 -*-

import os
import pickle
from collections import namedtuple
from tornado.routing import Router, Matcher, RuleRouter, Rule, PathMatches


Resolve = namedtuple('Resolve', ['filename', 'linenum', 'paths'])

Route = namedtuple('Route', ['endpoint', 'filename', 'linenum'])


def dict_decode_values(_dict):
    """
    {'foo': b'bar'} => {'foo': 'bar'}
    """
    return {
        key: value.decode('utf-8')
        for key, value in _dict.items()
    }


class CustomRouter(Router):
    def __init__(self, filename, linenum):
        self.filename = filename
        self.linenum = linenum

    def find_handler(self, request, **kwargs):
        return Resolve(
            filename=self.filename,
            linenum=self.linenum,
            paths=dict_decode_values(kwargs.get('path_kwargs', {}))
        )


class MethodMatches(Matcher):
    """Matches requests method"""

    def __init__(self, method):
        self.method = method.upper()

    def match(self, request):
        if request.method == self.method:
            return {}
        else:
            return None


class Router(RuleRouter):

    def __init__(self, routes_file):
        self.routes_file = routes_file
        self.rules = []
        self._cache = {}

        if os.path.exists(routes_file):
            # Server restarted, load the cache of routes
            with open(routes_file, 'rb') as file:
                self._cache = pickle.load(file)
            self._rebuild()

    def register(self, method, endpoint, filename, linenum):
        self._cache.setdefault(method, set())\
                   .add(Route(endpoint, filename, linenum))
        self._rebuild()

    def unregister(self, method, endpoint, filename, linenum):
        self._cache.get(method, set())\
                   .remove(Route(endpoint, filename, linenum))
        self._rebuild()

    def _rebuild(self):
        """Resolves a uri to the Story and line number to execute."""

        method_rules = []
        for method, routes in self._cache.items():
            rules = [
                Rule(
                    PathMatches(route.endpoint),
                    CustomRouter(route.filename, route.linenum)
                ) for route in routes
            ]
            # create a new rule by method mapping to many rule by path
            method_rules.append(Rule(MethodMatches(method), RuleRouter(rules)))

        # replace rules
        self.rules = method_rules

        # save route to file
        with open(self.routes_file, 'wb') as file:
            # [TODO] only works for one server
            pickle.dump(self._cache, file)
