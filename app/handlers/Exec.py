# -*- coding: utf-8 -*-
import ujson

import tornado

from raven.contrib.tornado import SentryMixin
from tornado.gen import coroutine, Future
from tornado.httpclient import AsyncHTTPClient
from tornado.log import app_log
from tornado.web import RequestHandler, HTTPError

from ..Router import Resolve


class ExecHandler(SentryMixin, RequestHandler):
    buffer = bytearray()

    def get_request_body(self):
        headers = self.request.headers
        if 'multipart/form-data' in headers.get('Content-Type', ''):
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
            'response': {}
        }

        return resolve, context

    def resolve_by_filename(self, path):
        """
        A http request to `/~/folder/story:3` will directly execute that story.
        """
        if ':' in path:
            path, block = tuple(path.split(':', 1))
        else:
            block = 1

        # [TODO] HTTPError(404) if filename does not exist

        resolve = Resolve(
            filename=path,
            block=block,
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
            'block': resolve.block,
            'json_context': context
        }
        params = ujson.dumps(data)

        url = 'http://%s/story/run' % self.application.settings['engine_addr']

        request = tornado.httpclient.HTTPRequest(
            method='POST',
            url=url,
            connect_timeout=10,
            request_timeout=60,
            body=params,
            streaming_callback=self._callback)

        http_client = AsyncHTTPClient()
        yield http_client.fetch(request)

        self.finish()

    def _callback(self, chunk):
        """
        Chunk examples that come from the Engine
            set_status 200
            set_header {"name":"X-Data", "value":"Asyncy"}
            write Hello, world
            ~finish~ will not be passed since it will close the connection
        """

        # Read `chunk` byte by byte and add it to the buffer.
        # When a byte is \n, then parse everything in the buffer as string,
        # and interpret the resulting JSON string.

        instructions = []
        for b in chunk:
            if b == 0x0A:  # 0x0A is an ASCII/UTF-8 new line.
                instructions.append(self.buffer.decode('utf-8'))
                self.buffer.clear()
            else:
                self.buffer.append(b)

        # If we have any new instructions, execute them.
        for ins in instructions:
            ins = ujson.loads(ins)
            command = ins['command']
            if command == 'set_status':
                self.set_status(ins['code'])
            elif command == 'set_header':
                self.set_header(ins['key'], ins['value'])
            elif command == 'write':
                self.write(ins['content'])
            elif command == 'finish':
                pass  # Do nothing.
            else:
                raise NotImplementedError(f'{command} is not implemented!')

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
