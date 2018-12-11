# -*- coding: utf-8 -*-
import pkgutil

from tornado.web import RequestHandler


class FourOhFour:

    content_404 = pkgutil.get_data('app', f'static/404.html')

    @classmethod
    def handle(cls, request_handler: RequestHandler):
        request_handler.set_status(404, reason='Not found')
        request_handler.write(cls.content_404)
