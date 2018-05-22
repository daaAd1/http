# -*- coding: utf-8 -*-

import os
from tornado import ioloop
from tornado.options import define, options
from raven.contrib.tornado import AsyncSentryClient

from .App import App
from . import handlers


define('debug', default=False, help='enable debug')
define('port',
       default=int(os.getenv('PORT', '8888')),
       help='port to listen on')
define('sentry_dsn',
       default=os.getenv('SENTRY_DSN'),
       help='Sentry DSN')
define('engine_addr',
       default=os.getenv('ENGINE_ADDR', 'engine:8888'),
       help='engine hostname:port')
define('routes_file',
       default=os.getenv('ROUTES_FILE',
                         os.path.join(os.path.dirname(__file__),
                                      '../routes.cache')),
       help='file location for caching routes')


def make_app():

    _handlers = [
        (r'/\+', handlers.RegisterHandler),
        (r'/(?P<is_file>~/)?(?P<path>.*)', handlers.ExecHandler)
    ]

    app = App(
        handlers=_handlers,
        debug=options.debug,
        engine_addr=options.engine_addr,
        routes_file=options.routes_file
    )

    app.sentry_client = AsyncSentryClient(options.sentry_dsn)

    return app


if __name__ == '__main__':
    options.parse_command_line()
    app = make_app()
    app.listen(options.port)
    ioloop.IOLoop.current().start()
