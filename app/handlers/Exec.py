# -*- coding: utf-8 -*-
from json import dumps
from raven.contrib.tornado import SentryMixin
from tornado.gen import coroutine, Future
from tornado.httpclient import AsyncHTTPClient
from tornado.log import app_log
from tornado.web import RequestHandler, HTTPError

from ..utils.Router import Resolve


class ExecHandler(SentryMixin, RequestHandler):
    def get_request_body(self):
        if 'multipart/form-data' in self.request.headers.get('Content-Type'):
            return self.request.files
        else:
            return self.request.body.decode('utf-8')

    def resolve_by_uri(self, path):
        """
        A http request to `/*` will resolve to one listener on that channel.
        """
        resolve = self.application.router.find_handler(self.request)

        app_log.info(f'Resolving to {repr(resolve)}')

        if not resolve:
            # exit: path not being followed
            if self.request.method == 'GET':
                raise HTTPError(404)
            else:
                raise HTTPError(405)

        context = {
            'request': {
                'method': self.request.method,
                'uri': self.request.uri,
                'paths': resolve.paths,
                'body': self.get_request_body(),
                'arguments': {k: self.get_argument(k) for k in self.request.arguments},
                'headers': dict(self.request.headers)
            },
            'response': { }
        }

        return resolve, context

    def resolve_by_filename(self, path):
        """
        A http request to `/~/folder/story:3` will directly execute that story.
        """
        if ':' in path:
            path, linenum = tuple(path.split(':', 1))
        else:
            linenum = 1

        # [TODO] HTTPError(404) if filename does not exist

        resolve = Resolve(
            filename=path,
            linenum=linenum,
            paths=None
        )

        context = self.get_request_body()

        return resolve, context

    @coroutine
    def _handle(self, is_file, path):
        if is_file:
            # resolve directly to story by pathname
            resolve, context = self.resolve_by_filename(path)
        else:
            # resolve to http listeners
            resolve, context = self.resolve_by_uri(path)

        # geneate the parameters for Engine
        data = {
            'story_name': resolve.filename,
            'start': resolve.linenum,
            'json_context': context
        }

        yield AsyncHTTPClient().fetch(
            f'http://{self.application.settings["engine_addr"]}',
            body=dumps(data),
            streaming_callback=self._callback,
            request_timeout=60
        )

        self.finish()

    def _callback(self, chunk):
        """
        Chunk examples that come from the Engine
            set_status 200
            set_header {"name":"X-Data", "value":"Asyncy"}
            write Hello, world
            ~finish~ will not be passed since it will close the connection
        """
        command, data = chunk.split(' ', 1)

        if command == 'set_status':
            self.set_status(data)

        elif command == 'set_header':
            args = loads(args)
            self.set_header(args['name'], args['value'])

        elif command == 'write':
            self.write(data)

    @coroutine
    def head(self, is_file, path):
        yield self._handle(is_file, path)

    @coroutine
    def get(self, is_file, path):
        yield self._handle(is_file, path)

    @coroutine
    def post(self, is_file, path):
        yield self._handle(is_file, path)

    @coroutine
    def delete(self, is_file, path):
        yield self._handle(is_file, path)

    @coroutine
    def patch(self, is_file, path):
        yield self._handle(is_file, path)

    @coroutine
    def put(self, is_file, path):
        yield self._handle(is_file, path)

    def options(self, is_file, path):
        """
        Returns the allowed options for this endpoint
        """
        self.set_header('Allow', 'GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS')
        # [FUTURE] http://zacstewart.com/2012/04/14/http-options-method.html
        self.finish()
