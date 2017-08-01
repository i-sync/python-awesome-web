#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
Url Handlers
'''

import re, time, json, logging, hashlib, base64, asyncio

from coreweb import  get, post

from models import User, Comment, Blog, next_id
from aiohttp import web

@get('/')
@asyncio.coroutine
def index(request):
    users = yield from User.find_all()
    return {
        '__template__': 'test.html',
        'users': users
    }

@get('/test')
def test(request):
    return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')