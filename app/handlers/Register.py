# -*- coding: utf-8 -*-

from json import loads
from raven.contrib.tornado import SentryMixin
from tornado.web import RequestHandler, HTTPError


class RegisterHandler(SentryMixin, RequestHandler):
    def post(self, action):
        """
        (un)Register a route
        """
        req = loads(self.request.body)
        if self.request.path == '/register':
            self.application.router.register(
                req['data'].get('method', 'get'),
                req['data']['path'],
                req['endpoint'])
            self.set_status(201)
        else:
            self.application.router.unregister(
                req['data'].get('method', 'get'),
                req['data']['path'],
                req['endpoint'])
            self.set_status(204)
