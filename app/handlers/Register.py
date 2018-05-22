# -*- coding: utf-8 -*-

from json import loads
from raven.contrib.tornado import SentryMixin
from tornado.web import RequestHandler, HTTPError


class RegisterHandler(SentryMixin, RequestHandler):
    def post(self, action):
        """
        (un)Register a route
        """
        data = loads(self.request.body)
        if action == 'register':
            self.application.router.register(**data)
            self.set_status(201)
        else:
            self.application.router.unregister(**data)
            self.set_status(204)
