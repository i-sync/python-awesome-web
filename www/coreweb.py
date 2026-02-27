#!/usr/bin/env python
# _*_ coding: utf-8 _*_


import os
import asyncio
import inspect
import functools
import json
from urllib import parse
from aiohttp import web
from apis import APIError
from logger import logger

def get(path):
    '''
    Define Decorator @Get('/path')
    :param path:
    :return:
    '''
    def decorator(func):
        func.__method__ = 'GET'
        func.__route__ = path
        return func
    return decorator

def post(path):
    '''
    Define Decorator @Post('/path')
    :param path:
    :return:
    '''
    def decorator(func):
        func.__method__ = 'POST'
        func.__route__ = path
        return func
    return decorator

def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)

    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters

    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: {}{}'.format(fn.__name__, str(sig)))
    return found

class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._requested_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._requested_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: {}'.format(request.content_type))
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                #remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            #check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logger.warning('Duplicate arg name in named arg and args:{}'.format(k))
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        #check required kw:
        if self._requested_kw_args:
            for name in self._requested_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument:{}'.format(name))
        logger.info('call with args: {}'.format(str(kw)))
        try:
            r = await self._func(**kw)
            return await build_response(self._app, request, r)
        except APIError as e:
            return await build_response(self._app, request, dict(error=e.error, data=e.data, message=e.message))


async def build_response(app, request, result):
    if isinstance(result, web.StreamResponse):
        return result
    if isinstance(result, bytes):
        return web.Response(body=result, content_type='application/octet-stream')
    if isinstance(result, str):
        if result.startswith('redirect:'):
            return web.HTTPFound(result[9:])
        return web.Response(body=result.encode('utf-8'), content_type='text/html', charset='utf-8')
    if isinstance(result, dict):
        template = result.get('__template__')
        if template is None:
            return web.Response(
                body=json.dumps(result, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'),
                content_type='application/json',
                charset='utf-8',
            )
        # Lazy import avoids circular imports during module loading.
        from config import configs
        from handlers import get_categories

        result['__user__'] = getattr(request, '__user__', None)
        result['web_meta'] = configs.web_meta
        result['categories'] = await get_categories()
        return web.Response(
            body=app['__templating__'].get_template(template).render(**result).encode('utf-8'),
            content_type='text/html',
            charset='utf-8',
        )
    if isinstance(result, int) and 100 <= result < 600:
        return web.Response(status=result)
    if isinstance(result, tuple) and len(result) == 2:
        status, message = result
        if isinstance(status, int) and 100 <= status < 600:
            return web.Response(status=status, text=str(message))
    return web.Response(body=str(result).encode('utf-8'), content_type='text/plain', charset='utf-8')

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logger.info('add static {} = {}'.format('/static/', path))

def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@Get or @Post not defined in {}.'.format(str(fn)))
    if not asyncio.iscoroutinefunction(fn):
        original_fn = fn

        @functools.wraps(original_fn)
        async def wrapped(*args, **kwargs):
            result = original_fn(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        fn = wrapped
    logger.info('add route {} {} => {}({})'.format(method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
