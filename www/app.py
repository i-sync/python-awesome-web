#!/usr/bin/env python
# _*_ coding: utf-8 _*_

from logger import logger
import os.path
import json
import time
import os
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
import orm
from coreweb import add_routes, add_static
from handlers import cookie2user, COOKIE_NAME, get_categories
from config import configs

def init_jinja2(app, **kwargs):
    logger.info('init jinja2...')
    options = dict(
        autoescape=kwargs.get('autoescape', True),
        block_start_string=kwargs.get('block_start_string', '{%'),
        block_end_string=kwargs.get('blcok_end_string', '%}'),
        variable_start_string=kwargs.get('variable_start_string', '{{'),
        variable_end_string=kwargs.get('variable_end_string', '}}'),
        auto_reload=kwargs.get('auto_reload', True),
    )
    path = kwargs.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logger.info('set jinja2 template path: {}'.format(path))
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kwargs.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def logger_factory(app, handler):

    async def inner_logger(request):
        logger.info('Request: {} {}'.format(request.method, request.path))
        # await asyncio.sleep(0.3)
        return await handler(request)
    return inner_logger


async def data_factory(app, handler):

    async def parse_data(request):
        if request.method == 'POST':
            content_type = request.content_type or ''
            if content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logger.info('request json: {}'.format(str(request.__data__)))
            elif content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logger.info('request form: {}'.format(str(request.__data__)))
        return await handler(request)
    return parse_data


async def auth_factory(app, handler):
    async def auth(request):
        logger.info('check user: {} {}'.format(request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logger.info('set current user: {}'.format(user.email))
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return await handler(request)
    return auth


async def response_factory(app, handler):

    async def response(request):
        logger.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            res = web.Response(body=r)
            res.content_type = 'application/octet-stream'
            return res
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            res = web.Response(body=r.encode('utf-8'))
            res.content_type = 'text/html'
            res.charset = 'utf-8'
            return res
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                res = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                res.content_type = 'application/json'
                res.charset = 'utf-8'
                return res
            r['__user__'] = request.__user__
            r['web_meta'] = configs.web_meta
            r['categories'] = await get_categories()
            res = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
            res.content_type = 'text/html'
            res.charset = 'utf-8'
            return res
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(status=r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(status=t, text=str(m))
        #default:
        return web.Response(body=str(r).encode('utf-8'), content_type='text/plain', charset='utf-8')
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
    return u'<span title="{}">{}</span>'.format(str_date, date_time.strftime("%Y-%m-%d"))

def ensure_http(url):
    if url.startswith("http") or url.startswith("https"):
        return url
    return "http://" + url


#def index(request):
    #return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')

async def init_db(app):
    logger.info(configs.database)
    await orm.create_pool(**configs.database)


async def close_db(app):
    await orm.destroy_pool()


def create_app():
    app = web.Application(middlewares=[logger_factory, auth_factory])
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    init_jinja2(app, filters=dict(datetime=datetime_filter, ensure_http=ensure_http))
    add_routes(app, 'handlers')
    add_static(app)
    return app


def main():
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '9000'))
    logger.info('Server started at http://{}:{}...'.format(host, port))
    web.run_app(create_app(), host=host, port=port)


if __name__ == '__main__':
    main()
