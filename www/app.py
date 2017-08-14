#!/usr/bin/env python
# _*_ coding: utf-8 _*_


import logging
import asyncio
import json
import time
import os
from datetime import  datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
import orm
from coreweb import add_routes, add_static
from handlers import cookie2user, COOKIE_NAME, get_categories
from config import configs

logging.basicConfig(level = logging.INFO)

def init_jinja2(app, **kwargs):
    logging.info('init jinja2...')
    options = dict(
        autoescape = kwargs.get('autoescape', True),
        block_start_string = kwargs.get('block_start_string', '{%'),
        block_end_string = kwargs.get('blcok_end_string', '%}'),
        variable_start_string = kwargs.get('variable_start_string', '{{'),
        variable_end_string = kwargs.get('variable_end_string', '}}'),
        auto_reload = kwargs.get('auto_reload', True)
    )
    path = kwargs.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: {}'.format(path))
    env = Environment(loader = FileSystemLoader(path), **options)
    filters = kwargs.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info('Request: {} {}'.format(request.method, request.path))
        # await asyncio.sleep(0.3)
        return (yield from handler(request))
    return logger

@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: {}'.format(str(request.__data__)))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: {}'.format(str(request.__data__)))
        return (yield from handler(request))
    return parse_data

@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user: {} {}'.format(request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                logging.info('set current user: {}'.format(user.email))
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth

@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = yield from handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            res = web.Response(body = r)
            res.content_type = 'application/octet-stream'
            return res
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            res = web.Response(body = r.encode('utf-8'))
            res.content_type = 'text/html; charset=utf-8'
            return res
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                res = web.Response(body = json.dumps(r, ensure_ascii = False, default = lambda o: o.__dict__).encode('utf-8'))
                res.content_type = 'application/json;charset=utf-8'
                return res
            else:
                r['__user__'] = request.__user__
                r['web_meta'] = configs.web_meta
                r['categories'] = yield from get_categories()
                res = web.Response(body = app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                res.content_type = 'text/html;charset=utf-8'
                return res
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        #default:
        res = web.Request(body = str(r).encode('utf-8'))
        res.content_type = 'text/plain;charset=utf-8'
        return res
    return response

def datetime_filter(t):
    date_time = datetime.fromtimestamp(t)
    str_date = date_time.strftime("%Y-%m-%d %X")
    delta = int(time.time() - t)
    if delta < 60:
        return u'<span title="{}">1分钟前</span>'.format(str_date)
    if delta < 3600:
        return u'<span title="{}">{}分钟前</span>'.format(str_date, delta // 60)
    if delta < 86400:
        return u'<span title="{}">{}小时前</span>'.format(str_date, delta // 3600)
    if delta < 604800:
        return u'<span title="{}">{}天前</span>'.format(str_date, delta // 86400)
    #dt = datetime.fromtimestamp(t)
    return u'<span title="{}">{}</span>'.format(str_date, date_time.strftime("%Y年%m月%d日"))



#def index(request):
    #return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')

@asyncio.coroutine
def init(loop):
    #app = web.Application(loop = loop, host = '127.0.0.1', port = 3306, user = 'root', password = '123', database = 'awesome')
    yield from orm.create_pool(loop = loop, **configs.database)
    app = web.Application(loop = loop, middlewares = [
        logger_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters = dict(datetime = datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    #app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), 'localhost', 8080)
    logging.info('Server started at http://127.0.0.1:8080...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
