#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
Url Handlers
'''

import re, time, json, logging, hashlib, base64, asyncio

from apis import APIValueError, APIError
from coreweb import  get, post

from models import User, Comment, Blog, next_id
from aiohttp import web
from config import configs

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
COOKIE_NAME = 'awesome_session'
_COOKIE_KEY = configs.session.secret

def user2cookie(user, max_age):
    '''
    Generate cookie str by user
    :param user:
    :param max_age:
    :return:
    '''

    expires = str(int(time.time() + max_age))
    s = '{}-{}-{}-{}'.format(user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid
    :param cookie_str:
    :return:
    '''

    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None

        s = '{}-{}-{}-{}'.format(uid, user.password, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('cookie:{} is invalid, invalid sha1')
            return None
        user.password = '*' * 8
        return user
    except Exception as e:
        logging.exception(e)
        return None

'''
@get('/')
@asyncio.coroutine
def index(request):
    users = yield from User.find_all()
    return {
        '__template__': 'test.html',
        'users': users
    }
'''

@get('/')
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


@get('/api/users')
def api_get_users():
    users = yield from User.find_all(order_by='created_at desc')
    for u in users:
        u.password = '*' * 8
    return dict(users = users)

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('User signed out.')
    return r

@post('/api/users')
def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_SHA1.match(password):
        raise APIValueError('password')

    users = yield from User.find_all('email=?', [email])
    if len(users) > 0:
        raise APIError('Register failed', 'email', 'Email is already in use.')

    uid = next_id()
    sha1_password = '{}:{}'.format(uid, password)
    logging.info('register password:{}, sha1_password:{}'.format(password, sha1_password))
    user = User(id=uid, name= name.strip(), email= email, password = hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/{}?d=mm&s=120'.format(hashlib.md5(email.encode('utf-8')).hexdigest()))
    yield from user.save()

    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '*' * 8
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@post('/api/authenticate')
def authenticate(*, email, password):
    if not email:
        raise APIValueError('email', 'Invalid Email')
    if not password:
        raise APIValueError('password', 'Invalid Password')
    users = yield from User.find_all('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')

    user = users[0]

    #check password
    sha1_password = '{}:{}'.format(user.id, password)
    logging.info('login password:{}, sha1_password:{}'.format(password, sha1_password))
    if user.password != hashlib.sha1(sha1_password.encode('utf-8')).hexdigest():
        raise APIValueError('password', 'Invalid Password.')
    # authenticate ok, set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '*' * 8
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r