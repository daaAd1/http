# -*- coding: utf-8 -*-
from datetime import datetime
import uuid

import ujson

import tornado

from raven.contrib.tornado import SentryMixin
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from tornado.log import app_log
from tornado.web import RequestHandler, HTTPError


class ExecHandler(SentryMixin, RequestHandler):
    buffer = bytearray()

    def prepare(self):
        self.set_header('Server', 'Asyncy')

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

        event = {
            'eventType': 'http_request',
            'cloudEventsVersion': '0.1',
            'source': 'gateway',
            'eventID': str(uuid.uuid4()),
            'eventTime': datetime.utcnow().replace(microsecond=0).isoformat(),
            'contentType': 'application/json',
            'data': {
                'headers': dict(self.request.headers)
            }
        }

        if 'application/json' in self.request.headers.get('content-type', ''):
            event['data']['body'] = ujson.loads(
                self.request.body.decode('utf-8'))

        return resolve, event

    @coroutine
    def _handle(self, path):
        resolve, event = self.resolve_by_uri(path)

        url = resolve.endpoint

        request = tornado.httpclient.HTTPRequest(
            method='POST',
            url=url,
            connect_timeout=10,
            request_timeout=60,
            body=ujson.dumps(event),
            headers={'Content-Type': 'application/json; charset=utf-8'},
            streaming_callback=self._callback)

        http_client = AsyncHTTPClient()
        try:
            yield http_client.fetch(request)
        except:
            import traceback
            traceback.print_exc()
            self.set_status(500, reason='Story execution failed')
            self.write('HTTP 500: Story execution failed\n')

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
            if command == 'write':
                self.write(ins['content'])
                if ins.get('flush'):
                    self.flush()
            elif command == 'set_status':
                self.set_status(ins['code'])
            elif command == 'set_cookie':
                # name, value, domain, expires, path, expires_days, secure
                if ins.pop('secure', False):
                    self.set_cookie(**ins)
                else:
                    self.set_secure_cookie(**ins)
            elif command == 'clear_cookie':
                # name, domain, path
                self.clear_cookie(**ins)
            elif command == 'clear_all_cookie':
                # domain, path
                self.clear_cookie(**ins)
            elif command == 'set_header':
                self.set_header(ins['key'], ins['value'])
            elif command == 'flush':
                self.flush()
            elif command == 'finish':
                # can we close quicker here?
                break
            else:
                raise NotImplementedError(f'{command} is not implemented!')

    @coroutine
    def head(self, path):
        yield self._handle(path)

    @coroutine
    def get(self, path):
        yield self._handle(path)

    @coroutine
    def post(self, path):
        yield self._handle(path)

    @coroutine
    def delete(self, path):
        yield self._handle(path)

    @coroutine
    def patch(self, path):
        yield self._handle(path)

    @coroutine
    def put(self, path):
        yield self._handle(path)

    def options(self, path):
        """
        Returns the allowed options for this endpoint
        """
        self.set_header('Allow', 'GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS')
        # [FUTURE] http://zacstewart.com/2012/04/14/http-options-method.html
        self.finish()
