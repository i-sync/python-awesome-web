#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
Url Handlers
'''
from logger import logger
import re, time, json, hashlib, base64, asyncio
import markdown2

from apis import APIValueError, APIError, APIResourceNotFoundError, APIPermissionError, Page
from coreweb import get, post

from models import User, Comment, CommentAnonymous, Blog, Category, Tags, next_id
from aiohttp import web
from config import configs

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA256 = re.compile(r'^[0-9a-f]{64}$')
COOKIE_NAME = configs.cookie.name
_COOKIE_KEY = configs.cookie.secret

COLORS = ["red","orange","yellow","olive","green","teal","blue","violet","purple","pink","brown","grey","black"]

'''
================== function ====================
'''
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

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



async def cookie2user(cookie_str):
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
        user = await User.find(uid)
        if user is None:
            return None

        s = '{}-{}-{}-{}'.format(uid, user.password, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logger.info('cookie:{} is invalid, invalid sha1')
            return None
        user.password = '*' * 8
        return user
    except Exception as e:
        logger.exception(e)
        return None

def text2html(text):
    lines = map(lambda s: '<p>{}</p>'.format(s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


async def get_categories():
    categories = await Category.find_all(order_by='created_at desc')
    return categories

def get_ip(request):
    host = request.headers.get('X-FORWARDED-FOR',None)
    if host is not None:
        logger.info("Get remote_ip from header, host: " + host)
        return host
    peername = request.transport.get_extra_info('peername')
    logger.info(peername)
    if peername is not None:
        host, port, *_ = peername
        return host
    else:
        return None

'''
====================== end function ====================
'''

'''
@get('/')
@asyncio.coroutine
def index(request):
    users = await User.find_all()
    return {
        '__template__': 'test.html',
        'users': users
    }
'''


'''
===================== client page =======================
'''
@get('/')
async def index(*, page = '1'):
    '''
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test blog', summary = summary, created_at = time.time()-120),
        Blog(id='2', name='Javascript IT', summary = summary, created_at = time.time()-3600),
        Blog(id='3', name='Learn Swift', summary = summary, created_at = time.time()-7200),
        Blog(id='4', name='Test blog', summary = summary, created_at = time.time()-120),
        Blog(id='5', name='Javascript IT', summary = summary, created_at = time.time()-3600),
        Blog(id='6', name='Learn Swift', summary = summary, created_at = time.time()-7200),
    ]
    '''
    page_index = get_page_index(page)
    num = await Blog.find_number('count(id)', where='name!=? and enabled=?', args=['__about__', True])
    page = Page(num, page_index)
    if num <= 0:
        blogs = []
    else:
        blogs = await Blog.find_all(where='name!=? and enabled=?', args=['__about__', True], order_by='created_at desc', limit=(page.offset, page.limit))
        for blog in blogs:
            blog.html_summary = markdown2.markdown(blog.summary, extras = ['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")
            #comments_count = await Comment.find_number(select_field='count(id)', where='blog_id=?', args=[blog.id])
            comments_count = await CommentAnonymous.find_number(select_field='count(id)', where='blog_id=?', args=[blog.id])
            blog.comments_count = comments_count

            #get blog tags
            tags = []
            if blog.tags:
                for tag_id in blog.tags.split(","):
                    tag = await Tags.find(tag_id)
                    if tag:
                        tags.append({"key": tag.id, "value": tag.name, "color": COLORS[tag.id%len(COLORS)]})
            blog.tags = tags
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs,
        'meta': {"keywords": configs.web_meta.keywords, "description": configs.web_meta.description }
    }

@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    logger.info('blog id is :{}'.format(id))
    if not blog:
        raise APIValueError('id', 'can not find blog id is :{}'.format(id))
    if not blog.enabled:
        raise APIResourceNotFoundError('id', 'Sorry, This articale can\'t find now, Please try it again later...')

    blog.view_count += 1
    await blog.update()
    #comments = await Comment.find_all('blog_id=?', [id], order_by='created_at desc')
    comments = await CommentAnonymous.find_all('blog_id=?', [id], order_by='created_at asc')

    tags = []
    if blog.tags:
        for tag_id in blog.tags.split(","):
            tag = await Tags.find(tag_id)
            if tag:
                tags.append({"key": tag.id, "value": tag.name, "color": COLORS[tag.id%len(COLORS)]})

    blog.keywords = ",".join([x["value"] for x in tags])
    blog.tags = tags
    for c in comments:
        c.html_content = markdown2.markdown(c.content, extras=['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")
    blog.html_content = markdown2.markdown(blog.content, extras=['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/test')
def test(request):
    return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')



@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin(request):
    if request.__user__: #user has login, redirect /
        r = web.HTTPFound('/')
        return r
    return {
        '__template__': 'signin.html'
    }

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logger.info('User signed out.')
    return r

@get('/user/{id}')
async def get_user(*, id):
    user = await User.find(id)
    if not user:
        raise APIValueError('id', 'can not find user, id:{}'.format(id))
    return {
        '__template__': 'user.html',
        'user_info': user
    }

@get('/category/{id}')
async def get_category_blogs(request, *, id, page='1'):
    category = await Category.find(id)
    if not category:
        raise APIValueError('category id', 'can not find category, by id:{}'.format(id))

    page_index = get_page_index(page)
    num = await Blog.find_number('count(id)', 'category_id=?', [id])
    page = Page(num, page_index)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.find_all(where='category_id=?',args=[id], order_by='created_at desc', limit=(page.offset, page.limit))
        for blog in blogs:
            blog.html_summary = markdown2.markdown(blog.summary, extras = ['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")
            comments_count = await Comment.find_number(select_field='count(id)', where='blog_id=?', args=[blog.id])
            blog.comments_count = comments_count

            #get blog tags
            tags = []
            if blog.tags:
                for tag_id in blog.tags.split(","):
                    tag = await Tags.find(tag_id)
                    if tag:
                        tags.append({"key": tag.id, "value": tag.name, "color": COLORS[tag.id%len(COLORS)]})
            blog.tags = tags
    return {
        '__template__': 'category.html',
        'page': page,
        'blogs': blogs,
        'category': category
    }

@get('/about')
async def get_about():
    about = await Blog.find_all(where='name=?', args=['__about__'])
    if len(about) == 0:
        raise APIResourceNotFoundError('about', 'can not find about page.')

    comments = await CommentAnonymous.find_all('blog_id=?', [about[0].id], order_by='created_at asc')
    for c in comments:
        c.html_content = markdown2.markdown(c.content, extras=['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")

    about[0].html_content = markdown2.markdown(about[0].content, extras = ['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']).replace("<table>", "<table class=\"ui celled table\">")
    about[0].view_count += 1
    await about[0].update()


    return {
        '__template__': 'about.html',
        'blog': about[0],
        'comments': comments
    }


'''
====================== end client page =====================
'''

'''
====================== manage page =========================
'''

@get('/manage/blogs/create')
async def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs',
        'alltags': json.dumps([{"key": tag.id, "value": tag.name} for tag in (await Tags.find_all())])
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/{}'.format(id)
    }

@get('/manage/blogs')
def manage_blogs(*, page = '1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/comments')
def manage_comments(*, page = '1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

@get('/manage/users')
def manage_user(*, page = '1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/manage/categories')
def manage_category(*, page = '1'):
    return {
        '__template__': 'manage_categories.html',
        'page_index': get_page_index(page)
    }

@get('/manage/categories/create')
def manage_create_categories():
    return {
        '__template__': 'manage_category_edit.html',
        'id': '',
        'action': '/api/categories'
    }

@get('/manage/categories/edit')
def manage_edit_categories(*, id):
    return {
        '__template__': 'manage_category_edit.html',
        'id': id,
        'action': '/api/categories/{}'.format(id)
    }

'''
==================== end manage page =================
'''


'''
==================== backend api ====================
'''

@get('/api/users')
async def api_get_users(request, *, page = '1'):
    '''get all users'''
    check_admin(request)
    page_index = get_page_index(page)
    num = await User.find_number('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page = p, users = ())
    users = await User.find_all(order_by='created_at desc', limit = (p.offset, p.limit))
    for u in users:
        u.password = '*' * 8
    return dict(page = p, users = users)

@post('/api/users')
async def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_SHA256.match(password):
        raise APIValueError('password')

    users = await User.find_all('email=?', [email])
    if len(users) > 0:
        raise APIError('Register failed', 'email', 'Email is already in use.')

    uid = next_id()
    sha1_password = '{}:{}'.format(uid, password)
    logger.info('register password:{}, sha1_password:{}'.format(password, sha1_password))
    user = User(id=uid, name= name.strip(), email= email, password = hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/{}?d=identicon&s=120'.format(hashlib.md5(name.encode('utf-8')).hexdigest()))
    await user.save()

    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '*' * 8
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@post('/api/authenticate')
async def authenticate(*, email, password, remember):
    if not email:
        raise APIValueError('email', 'Invalid Email')
    if not password:
        raise APIValueError('password', 'Invalid Password')
    users = await User.find_all('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist')

    user = users[0]

    #check password
    sha1_password = '{}:{}'.format(user.id, password)
    #logger.info('login password:{}, sha1_password:{}'.format(password, sha1_password))
    if user.password != hashlib.sha1(sha1_password.encode('utf-8')).hexdigest():
        raise APIValueError('password', 'Invalid Password.')
    # authenticate ok, set cookie
    r = web.Response()
    if remember:
        max_age = configs.cookie.max_age_long
    else:
        max_age = configs.cookie.max_age
    r.set_cookie(COOKIE_NAME, user2cookie(user, max_age), max_age=max_age, httponly=True)
    user.password = '*' * 8
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

'''-----------blogs------------'''
@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)

    tags = []
    if blog.tags:
        for tag_id in blog.tags.split(","):
            tag = await Tags.find(tag_id)
            if tag:
                tags.append({"key": tag.id, "value": tag.name})

    blog.tags = tags
    blog.alltags = [{"key": tag.id, "value": tag.name} for tag in (await Tags.find_all())]

    return blog

@get('/api/blogs')
async def api_blogs(*, page = '1'):
    page_index = get_page_index(page)
    num = await Blog.find_number('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page = p, blogs = ())
    blogs = await Blog.find_all(order_by='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@post('/api/blogs')
async def api_create_blog(request, *, name, description, summary, content, category_id, tags):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary can not be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty')

    category = await Category.find(category_id)
    if category:
        #raise APIValueError('category', 'can not find category, category_id:{}'.format(category_id))
        category_id= category.id
        category_name = category.name
    else:
        category_name =''

    tag_ids = []
    if len(tags) > 0:
        for tag in tags:
            if tag["key"]:
                rs = await Tags.find(tag["key"])
                if rs:
                    tag_ids.append(rs.id)
            else:
                rs =  await Tags.find_all("name=?", [tag["value"]])
                if len(rs) > 0:
                    tag_ids.append(rs[0].id)
                else: #create new tag
                    tag = Tags(name=tag["value"])
                    rows, lastrowid = await tag.save()
                    tag_ids.append(lastrowid)

    blog = Blog(user_id = request.__user__.id,
                user_name= request.__user__.name,
                user_image = request.__user__.image,
                category_id = category_id,
                category_name = category_name,
                name = name.strip(),
                description = description.strip(),
                summary = summary.strip(),
                content = content.strip(),
                tags = ",".join([str(id) for id in tag_ids]))
    await blog.save()
    return blog

@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
    logger.info('delete blog id: {}'.format(id))
    check_admin(request)
    blog = await Blog.find(id)
    if blog:
        await blog.remove()
        return blog
    raise APIValueError('id', 'id can not find...')

@post('/api/blogs/{id}')
async def api_edit_blog(request, *, id, name, description, summary, content, category_id, tags):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary can not be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty')
    #blog = Blog(user_id = request.__user__.id, user_name= request.__user__.name, user_image = request.__user__.image, name = name.strip(), summary = summary.strip(), content = content.strip())
    blog = await Blog.find(id)
    if not blog:
        raise APIValueError('id', 'request path error, id : {}'.format(id))

    category = await Category.find(category_id)
    if category:
        #raise APIValueError('category', 'can not find category, category_id:{}'.format(category_id))
        category_id= category.id
        category_name = category.name
    else:
        category_name =''

    tag_ids = []
    if len(tags) > 0:
        for tag in tags:
            if tag["key"]:
                rs = await Tags.find(tag["key"])
                if rs:
                    tag_ids.append(rs.id)
            else:
                rs =  await Tags.find_all("name=?", [tag["value"]])
                if len(rs) > 0:
                    tag_ids.append(rs[0].id)
                else: #create new tag
                    tag = Tags(name=tag["value"])
                    rows, lastrowid = await tag.save()
                    tag_ids.append(lastrowid)

    blog.name = name
    blog.description = description
    blog.summary = summary
    blog.content = content
    blog.category_id = category_id
    blog.category_name = category_name
    blog.tags = ",".join([str(id) for id in tag_ids])
    blog.updated_at = time.time()
    await blog.update()
    return blog

@post('/api/blogs/{id}/enabled')
async def api_enabled_blog(request, *, id, status):
    check_admin(request)
    blog = await Blog.find(id)
    if not blog:
        raise APIValueError('id', 'request id error, id : {}'.format(id))

    if isinstance(status, str) and status.isalpha():
        status = int(status.lower() == 'true')

    blog.enabled = status
    blog.updated_at = time.time()
    await blog.update()
    return blog

'''-----------comments-----------'''
@post('/api/blogs/{id}/comments')
async def api_create_blog_comments(request, *, id, content):
    '''create blog comments'''
    if not request.__user__:
        raise APIPermissionError('please login first.')

    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty.')

    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('blog', 'can not find blog, id :{}'.format(id))

    comment = Comment(blog_id = id, user_id= request.__user__.id, user_name = request.__user__.name, user_image = request.__user__.image, content = content.strip() )
    await comment.save()
    return comment

@get('/api/comments')
async def api_comments(request, *, page = '1'):
    '''get all comments.'''
    check_admin(request)
    page_index = get_page_index(page)
    num = await Comment.find_number('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page = p, comments = ())
    comments = await Comment.find_all(order_by = 'created_at desc', limit = (p.offset, p.limit))
    return dict(page = p, comments = comments)

@post('/api/comments/{comment_id}/delete')
async def api_delete_comments(request, *, comment_id):
    '''delete comment.'''
    check_admin(request)
    comment = await Comment.find(comment_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment', 'can not find comment, comment id: {}'.format(comment_id))
    await comment.remove()
    return comment

'''-----------comments_anonymous-----------'''
@post('/api/blogs/{blog_id}/comments_anonymous')
async def api_create_blog_comments_anonymous(request, *, parent_id, blog_id, target_name, content, name, email, website):
    '''create blog comments anonymous'''
    #if not request.__user__:
    #    raise APIPermissionError('please login first.')

    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty.')
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty.')
    #if not email or not email.strip():
    #   raise APIValueError('email', 'email can not be empty.')

    blog = await Blog.find(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('blog', 'can not find blog, id :{}'.format(id))

    avatar = 'http://www.gravatar.com/avatar/{}?d=identicon&s=120'.format(hashlib.md5(name.encode('utf-8')).hexdigest())

    comment_anonymous = CommentAnonymous(parent_id = parent_id, blog_id = blog_id, target_name = target_name, content = content.strip(), name = name.strip(), email = email.strip(), website = website.strip(), avatar = avatar, ip = get_ip(request) )
    await comment_anonymous.save()
    return comment_anonymous

@get('/api/comments_anonymous')
async def api_comments_anonymous(request, *, page = '1'):
    '''get all comments.'''
    check_admin(request)
    page_index = get_page_index(page)
    num = await CommentAnonymous.find_number('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page = p, comments = ())
    comments = await CommentAnonymous.find_all(order_by = 'created_at desc', limit = (p.offset, p.limit))
    return dict(page = p, comments = comments)

@post('/api/comments_anonymous/{comment_anonymous_id}/delete')
async def api_delete_comments_anonymous(request, *, comment_anonymous_id):
    '''delete comment.'''
    check_admin(request)
    comment = await CommentAnonymous.find(comment_anonymous_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment', 'can not find comment, comment id: {}'.format(comment_anonymous_id))
    await comment.remove()
    return comment

'''-----------categories-----------'''
@get('/api/categories')
async def api_categories(*, page = '1'):
    '''get all categories.'''
    page_index = get_page_index(page)
    num = await Category.find_number('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page = p, categories = ())
    categories = await Category.find_all(order_by = 'created_at desc', limit = (p.offset, p.limit))
    return dict(page = p, categories = categories)

@post('/api/categories')
async def api_create_category(request, *, name):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')
    category = Category(name = name)
    await category.save()
    return category

@get('/api/categories/{id}')
async def api_get_category(request, *, id):
    category = await Category.find(id)
    return category

@post('/api/categories/{id}')
async def api_edit_category(request, *, id, name):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')

    category = await Category.find(id)
    if not category:
        raise APIValueError('category', 'category can not be find, id:{}'.format(id))
    category.name = name
    await category.update()
    return category

@post('/api/categories/{id}/delete')
async def api_delete_category(request, *, id):
    logger.info('delete category id: {}'.format(id))
    check_admin(request)
    category = await Category.find(id)
    if category:
        await category.remove()
        return category
    raise APIValueError('id', 'id can not find...')

@post('/api/modify_password')
async def api_modify_password(request, *, password0, password1):
    #check_admin(request)
    if request.__user__ is None:
        raise APIPermissionError('You must login first!')
    if not password0 or not password0.strip():
        raise APIValueError('password0', 'old password can not be empty.')
    if not password1 or not _RE_SHA256.match(password1):
        raise APIValueError('password1', 'Invalid new password.')

    user = await User.find(request.__user__.id)
    if user is None:
        raise APIResourceNotFoundError('User not found')

    # check password
    sha1_password0 = '{}:{}'.format(user.id, password0)
    if user.password != hashlib.sha1(sha1_password0.encode('utf-8')).hexdigest():
        raise APIValueError('password0', 'Invalid Old Password.')

    #set new password
    sha1_password1 = '{}:{}'.format(user.id, password1)
    user.password = hashlib.sha1(sha1_password1.encode('utf-8')).hexdigest()
    user.updated_at = time.time()
    await user.update()

    return dict(user_id=user.id)
'''
==================== end backend api ====================
'''