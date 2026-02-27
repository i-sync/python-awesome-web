import hashlib
import re
import time

from app.apis import APIPermissionError
from app.config import configs
from app.db.models import Category, User
from app.logger import logger

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA256 = re.compile(r'^[0-9a-f]{64}$')
COOKIE_NAME = configs.cookie.name
_COOKIE_KEY = configs.cookie.secret

COLORS = ['red', 'orange', 'yellow', 'olive', 'green', 'teal', 'blue', 'violet', 'purple', 'pink', 'brown', 'grey', 'black']


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    page = 1
    try:
        page = int(page_str)
    except ValueError:
        pass
    if page < 1:
        page = 1
    return page


def parse_tag_id(tag_id):
    if isinstance(tag_id, int):
        return tag_id
    if tag_id is None:
        return None
    value = str(tag_id).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    payload = '{}-{}-{}-{}'.format(user.id, user.password, expires, _COOKIE_KEY)
    return '-'.join([user.id, expires, hashlib.sha1(payload.encode('utf-8')).hexdigest()])


async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        values = cookie_str.split('-')
        if len(values) != 3:
            return None
        uid, expires, sha1 = values
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None

        payload = '{}-{}-{}-{}'.format(uid, user.password, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(payload.encode('utf-8')).hexdigest():
            logger.info('cookie:{} is invalid, invalid sha1'.format(cookie_str))
            return None
        user.password = '*' * 8
        return user
    except Exception as ex:
        logger.exception(ex)
        return None


def text2html(text):
    lines = map(
        lambda s: '<p>{}</p>'.format(s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')),
        filter(lambda s: s.strip() != '', text.split('\n')),
    )
    return ''.join(lines)


async def get_categories():
    return await Category.find_all(order_by='created_at desc')


def get_ip(request):
    host = request.headers.get('X-FORWARDED-FOR', None)
    if host is not None:
        logger.info('Get remote_ip from header, host: {}'.format(host))
        return host
    peername = request.transport.get_extra_info('peername')
    logger.info(peername)
    if peername is not None:
        host, _port, *_ = peername
        return host
    return None
