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

@get('/blogs')
def blogs(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test blog', summary = summary, created_at = time.time()-120),
        Blog(id='2', name='Javascript IT', summary = summary, created_at = time.time()-3600),
        Blog(id='3', name='Learn Swift', summary = summary, created_at = time.time()-7200),
    ]

    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

@get('/test')
def test(request):
    return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')