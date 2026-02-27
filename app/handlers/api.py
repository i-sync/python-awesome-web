import hashlib
import json
import time

from aiohttp import web

from app.apis import APIError, APIPermissionError, APIResourceNotFoundError, APIValueError, Page
from app.config import configs
from app.coreweb import get, post
from app.db.models import Blog, Category, Comment, CommentAnonymous, Tags, User, next_id
from app.logger import logger

from app.handlers.common import (
    COOKIE_NAME,
    _RE_EMAIL,
    _RE_SHA256,
    check_admin,
    get_ip,
    get_page_index,
    parse_tag_id,
    user2cookie,
)


@get('/api/users')
async def api_get_users(request, *, page='1'):
    check_admin(request)
    page_index = get_page_index(page)
    total = await User.find_number('count(id)')
    pager = Page(total, page_index)
    if total == 0:
        return dict(page=pager, users=())
    users = await User.find_all(order_by='created_at desc', limit=(pager.offset, pager.limit))
    for user in users:
        user.password = '*' * 8
    return dict(page=pager, users=users)


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
    user = User(
        id=uid,
        name=name.strip(),
        email=email,
        password=hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(),
        image='http://www.gravatar.com/avatar/{}?d=identicon&s=120'.format(hashlib.md5(name.encode('utf-8')).hexdigest()),
    )
    await user.save()

    response = web.Response()
    response.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '*' * 8
    response.content_type = 'application/json'
    response.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return response


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
    sha1_password = '{}:{}'.format(user.id, password)
    if user.password != hashlib.sha1(sha1_password.encode('utf-8')).hexdigest():
        raise APIValueError('password', 'Invalid Password.')

    response = web.Response()
    if isinstance(remember, str):
        remember = remember.strip().lower() in ('true', '1', 'yes', 'on')
    max_age = configs.cookie.max_age_long if remember else configs.cookie.max_age
    response.set_cookie(COOKIE_NAME, user2cookie(user, max_age), max_age=max_age, httponly=True)
    user.password = '*' * 8
    response.content_type = 'application/json'
    response.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return response


@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)

    tags = []
    if blog.tags:
        for tag_id in blog.tags.split(','):
            tag = await Tags.find(parse_tag_id(tag_id))
            if tag:
                tags.append({'key': tag.id, 'value': tag.name})

    blog.tags = tags
    blog.alltags = [{'key': tag.id, 'value': tag.name} for tag in (await Tags.find_all())]
    return blog


@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    total = await Blog.find_number('count(id)')
    pager = Page(total, page_index)
    if total == 0:
        return dict(page=pager, blogs=())
    blogs = await Blog.find_all(order_by='created_at desc', limit=(pager.offset, pager.limit))
    return dict(page=pager, blogs=blogs)


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
        category_id = category.id
        category_name = category.name
    else:
        category_name = ''

    tag_ids = []
    if len(tags) > 0:
        for tag in tags:
            if tag['key']:
                tag_record = await Tags.find(parse_tag_id(tag['key']))
                if tag_record:
                    tag_ids.append(tag_record.id)
            else:
                tag_records = await Tags.find_all('name=?', [tag['value']])
                if len(tag_records) > 0:
                    tag_ids.append(tag_records[0].id)
                else:
                    new_tag = Tags(name=tag['value'])
                    _, tag_id = await new_tag.save()
                    tag_ids.append(tag_id)

    blog = Blog(
        user_id=request.__user__.id,
        user_name=request.__user__.name,
        user_image=request.__user__.image,
        category_id=category_id,
        category_name=category_name,
        name=name.strip(),
        description=description.strip(),
        summary=summary.strip(),
        content=content.strip(),
        tags=','.join([str(tag_id) for tag_id in tag_ids]),
    )
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

    blog = await Blog.find(id)
    if not blog:
        raise APIValueError('id', 'request path error, id : {}'.format(id))

    category = await Category.find(category_id)
    if category:
        category_id = category.id
        category_name = category.name
    else:
        category_name = ''

    tag_ids = []
    if len(tags) > 0:
        for tag in tags:
            if tag['key']:
                tag_record = await Tags.find(parse_tag_id(tag['key']))
                if tag_record:
                    tag_ids.append(tag_record.id)
            else:
                tag_records = await Tags.find_all('name=?', [tag['value']])
                if len(tag_records) > 0:
                    tag_ids.append(tag_records[0].id)
                else:
                    new_tag = Tags(name=tag['value'])
                    _, tag_id = await new_tag.save()
                    tag_ids.append(tag_id)

    blog.name = name
    blog.description = description
    blog.summary = summary
    blog.content = content
    blog.category_id = category_id
    blog.category_name = category_name
    blog.tags = ','.join([str(tag_id) for tag_id in tag_ids])
    blog.updated_at = time.time()
    await blog.update()
    return blog


@post('/api/blogs/{id}/enabled')
async def api_enabled_blog(request, *, id, status):
    check_admin(request)
    blog = await Blog.find(id)
    if not blog:
        raise APIValueError('id', 'request id error, id : {}'.format(id))

    if isinstance(status, str):
        value = status.strip().lower()
        if value in ('true', '1', 'yes', 'on'):
            status = True
        elif value in ('false', '0', 'no', 'off'):
            status = False
        else:
            status = bool(value)
    else:
        status = bool(status)

    blog.enabled = status
    blog.updated_at = time.time()
    await blog.update()
    return blog


@post('/api/blogs/{id}/comments')
async def api_create_blog_comments(request, *, id, content):
    if not request.__user__:
        raise APIPermissionError('please login first.')
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty.')

    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('blog', 'can not find blog, id :{}'.format(id))

    comment = Comment(
        blog_id=id,
        user_id=request.__user__.id,
        user_name=request.__user__.name,
        user_image=request.__user__.image,
        content=content.strip(),
    )
    await comment.save()
    return comment


@get('/api/comments')
async def api_comments(request, *, page='1'):
    check_admin(request)
    page_index = get_page_index(page)
    total = await Comment.find_number('count(id)')
    pager = Page(total, page_index)
    if total == 0:
        return dict(page=pager, comments=())
    comments = await Comment.find_all(order_by='created_at desc', limit=(pager.offset, pager.limit))
    return dict(page=pager, comments=comments)


@post('/api/comments/{comment_id}/delete')
async def api_delete_comments(request, *, comment_id):
    check_admin(request)
    comment = await Comment.find(comment_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment', 'can not find comment, comment id: {}'.format(comment_id))
    await comment.remove()
    return comment


@post('/api/blogs/{blog_id}/comments_anonymous')
async def api_create_blog_comments_anonymous(request, *, parent_id, blog_id, target_name, content, name, email, website):
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty.')
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty.')

    blog = await Blog.find(blog_id)
    if blog is None:
        raise APIResourceNotFoundError('blog', 'can not find blog, id :{}'.format(blog_id))

    avatar = 'http://www.gravatar.com/avatar/{}?d=identicon&s=120'.format(hashlib.md5(name.encode('utf-8')).hexdigest())

    comment_anonymous = CommentAnonymous(
        parent_id=parent_id,
        blog_id=blog_id,
        target_name=target_name,
        content=content.strip(),
        name=name.strip(),
        email=email.strip(),
        website=website.strip(),
        avatar=avatar,
        ip=get_ip(request),
    )
    await comment_anonymous.save()
    return comment_anonymous


@get('/api/comments_anonymous')
async def api_comments_anonymous(request, *, page='1'):
    check_admin(request)
    page_index = get_page_index(page)
    total = await CommentAnonymous.find_number('count(id)')
    pager = Page(total, page_index)
    if total == 0:
        return dict(page=pager, comments=())
    comments = await CommentAnonymous.find_all(order_by='created_at desc', limit=(pager.offset, pager.limit))
    return dict(page=pager, comments=comments)


@post('/api/comments_anonymous/{comment_anonymous_id}/delete')
async def api_delete_comments_anonymous(request, *, comment_anonymous_id):
    check_admin(request)
    comment = await CommentAnonymous.find(comment_anonymous_id)
    if comment is None:
        raise APIResourceNotFoundError('Comment', 'can not find comment, comment id: {}'.format(comment_anonymous_id))
    await comment.remove()
    return comment


@get('/api/categories')
async def api_categories(*, page='1'):
    page_index = get_page_index(page)
    total = await Category.find_number('count(id)')
    pager = Page(total, page_index)
    if total == 0:
        return dict(page=pager, categories=())
    categories = await Category.find_all(order_by='created_at desc', limit=(pager.offset, pager.limit))
    return dict(page=pager, categories=categories)


@post('/api/categories')
async def api_create_category(request, *, name):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name can not be empty')
    category = Category(name=name)
    await category.save()
    return category


@get('/api/categories/{id}')
async def api_get_category(request, *, id):
    return await Category.find(id)


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
    if request.__user__ is None:
        raise APIPermissionError('You must login first!')
    if not password0 or not password0.strip():
        raise APIValueError('password0', 'old password can not be empty.')
    if not password1 or not _RE_SHA256.match(password1):
        raise APIValueError('password1', 'Invalid new password.')

    user = await User.find(request.__user__.id)
    if user is None:
        raise APIResourceNotFoundError('User not found')

    sha1_password0 = '{}:{}'.format(user.id, password0)
    if user.password != hashlib.sha1(sha1_password0.encode('utf-8')).hexdigest():
        raise APIValueError('password0', 'Invalid Old Password.')

    sha1_password1 = '{}:{}'.format(user.id, password1)
    user.password = hashlib.sha1(sha1_password1.encode('utf-8')).hexdigest()
    user.updated_at = time.time()
    await user.update()

    return dict(user_id=user.id)
