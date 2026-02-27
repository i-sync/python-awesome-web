import json

from aiohttp import web

from app.apis import APIResourceNotFoundError, APIValueError, Page
from app.config import configs
from app.coreweb import get
from app.db.models import Blog, Category, Comment, CommentAnonymous, Tags, User
from app.logger import logger
from app.services.render import markdown_to_html

from app.handlers.common import COLORS, COOKIE_NAME, get_page_index, parse_tag_id


@get('/')
async def index(*, page='1'):
    page_index = get_page_index(page)
    current_page = Page(
        await Blog.find_number('count(id)', where='name!=? and enabled=?', args=['__about__', True]),
        page_index,
    )
    if current_page.item_count <= 0:
        blogs = []
    else:
        blogs = await Blog.find_all(
            where='name!=? and enabled=?',
            args=['__about__', True],
            order_by='created_at desc',
            limit=(current_page.offset, current_page.limit),
        )
        for blog in blogs:
            blog.html_summary = markdown_to_html(blog.summary)
            comments_count = await CommentAnonymous.find_number(select_field='count(id)', where='blog_id=?', args=[blog.id])
            blog.comments_count = comments_count

            tags = []
            if blog.tags:
                for tag_id in blog.tags.split(','):
                    tag = await Tags.find(parse_tag_id(tag_id))
                    if tag:
                        tags.append({'key': tag.id, 'value': tag.name, 'color': COLORS[tag.id % len(COLORS)]})
            blog.tags = tags

    return {
        '__template__': 'blogs.html',
        'page': current_page,
        'blogs': blogs,
        'meta': {'keywords': configs.web_meta.keywords, 'description': configs.web_meta.description},
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
    comments = await CommentAnonymous.find_all('blog_id=?', [id], order_by='created_at asc')

    tags = []
    if blog.tags:
        for tag_id in blog.tags.split(','):
            tag = await Tags.find(parse_tag_id(tag_id))
            if tag:
                tags.append({'key': tag.id, 'value': tag.name, 'color': COLORS[tag.id % len(COLORS)]})

    blog.keywords = ','.join([x['value'] for x in tags])
    blog.tags = tags
    for comment in comments:
        comment.html_content = markdown_to_html(comment.content)
    blog.html_content = markdown_to_html(blog.content)
    return {'__template__': 'blog.html', 'blog': blog, 'comments': comments}


@get('/test')
def test(request):
    return web.Response(body=b'<h1>Awesome Python3 Web</h1>', content_type='text/html')


@get('/register')
def register():
    return {'__template__': 'register.html'}


@get('/signin')
def signin(request):
    if request.__user__:
        return web.HTTPFound('/')
    return {'__template__': 'signin.html'}


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    response = web.HTTPFound(referer or '/')
    response.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logger.info('User signed out.')
    return response


@get('/user/{id}')
async def get_user(*, id):
    user = await User.find(id)
    if not user:
        raise APIValueError('id', 'can not find user, id:{}'.format(id))
    return {'__template__': 'user.html', 'user_info': user}


@get('/category/{id}')
async def get_category_blogs(request, *, id, page='1'):
    category = await Category.find(id)
    if not category:
        raise APIValueError('category id', 'can not find category, by id:{}'.format(id))

    page_index = get_page_index(page)
    current_page = Page(await Blog.find_number('count(id)', 'category_id=?', [id]), page_index)
    if current_page.item_count == 0:
        blogs = []
    else:
        blogs = await Blog.find_all(
            where='category_id=?',
            args=[id],
            order_by='created_at desc',
            limit=(current_page.offset, current_page.limit),
        )
        for blog in blogs:
            blog.html_summary = markdown_to_html(blog.summary)
            comments_count = await Comment.find_number(select_field='count(id)', where='blog_id=?', args=[blog.id])
            blog.comments_count = comments_count
            tags = []
            if blog.tags:
                for tag_id in blog.tags.split(','):
                    tag = await Tags.find(parse_tag_id(tag_id))
                    if tag:
                        tags.append({'key': tag.id, 'value': tag.name, 'color': COLORS[tag.id % len(COLORS)]})
            blog.tags = tags

    return {'__template__': 'category.html', 'page': current_page, 'blogs': blogs, 'category': category}


@get('/about')
async def get_about():
    about = await Blog.find_all(where='name=?', args=['__about__'])
    if len(about) == 0:
        raise APIResourceNotFoundError('about', 'can not find about page.')

    comments = await CommentAnonymous.find_all('blog_id=?', [about[0].id], order_by='created_at asc')
    for comment in comments:
        comment.html_content = markdown_to_html(comment.content)

    about[0].html_content = markdown_to_html(about[0].content)
    about[0].view_count += 1
    await about[0].update()

    return {'__template__': 'about.html', 'blog': about[0], 'comments': comments}
