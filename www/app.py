#!/usr/bin/env python
# _*_ coding: utf-8 _*_


import logging
import asyncio
import json
import time
import os
from datetime import  datetime
from aiohttp import web

logging.basicConfig(level = logging.INFO)

def index(request):
    return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop = loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '::', 8080)
    logging.info('Server started at http://127.0.0.1:8080...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
