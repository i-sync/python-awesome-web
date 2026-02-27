#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import os
from pathlib import Path
import time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from app.config import configs
from app.coreweb import add_routes, add_static
import app.db.orm as orm
from app.handlers import COOKIE_NAME, cookie2user
from app.logger import logger


def init_jinja2(app, **kwargs):
    logger.info('init jinja2...')
    options = dict(
        autoescape=kwargs.get('autoescape', True),
        block_start_string=kwargs.get('block_start_string', '{%'),
        block_end_string=kwargs.get('block_end_string', '%}'),
        variable_start_string=kwargs.get('variable_start_string', '{{'),
        variable_end_string=kwargs.get('variable_end_string', '}}'),
        auto_reload=kwargs.get('auto_reload', True),
    )
    path = kwargs.get('path', None)
    if path is None:
        path = str(Path(__file__).resolve().parent / 'templates')
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
        return await handler(request)

    return inner_logger


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


def datetime_filter(value):
    date_time = datetime.fromtimestamp(value)
    str_date = date_time.strftime('%Y-%m-%d %X')
    delta = int(time.time() - value)
    if delta < 60:
        return '<span title="{}">1分钟前</span>'.format(str_date)
    if delta < 3600:
        return '<span title="{}">{}分钟前</span>'.format(str_date, delta // 60)
    if delta < 86400:
        return '<span title="{}">{}小时前</span>'.format(str_date, delta // 3600)
    if delta < 604800:
        return '<span title="{}">{}天前</span>'.format(str_date, delta // 86400)
    return '<span title="{}">{}</span>'.format(str_date, date_time.strftime('%Y-%m-%d'))


def ensure_http(url):
    if url.startswith('http') or url.startswith('https'):
        return url
    return 'http://' + url


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
    for module in ('app.handlers.public', 'app.handlers.manage', 'app.handlers.api'):
        add_routes(app, module)
    add_static(app)
    return app


def main():
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '9000'))
    logger.info('Server started at http://{}:{}...'.format(host, port))
    web.run_app(create_app(), host=host, port=port)


if __name__ == '__main__':
    main()
