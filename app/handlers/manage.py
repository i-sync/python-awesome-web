import json

from app.coreweb import get
from app.db.models import Tags

from app.handlers.common import get_page_index


@get('/manage/blogs/create')
async def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs',
        'alltags': json.dumps([{'key': tag.id, 'value': tag.name} for tag in (await Tags.find_all())]),
    }


@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {'__template__': 'manage_blog_edit.html', 'id': id, 'action': '/api/blogs/{}'.format(id)}


@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {'__template__': 'manage_blogs.html', 'page_index': get_page_index(page)}


@get('/manage/comments')
def manage_comments(*, page='1'):
    return {'__template__': 'manage_comments.html', 'page_index': get_page_index(page)}


@get('/manage/users')
def manage_user(*, page='1'):
    return {'__template__': 'manage_users.html', 'page_index': get_page_index(page)}


@get('/manage/categories')
def manage_category(*, page='1'):
    return {'__template__': 'manage_categories.html', 'page_index': get_page_index(page)}


@get('/manage/categories/create')
def manage_create_categories():
    return {'__template__': 'manage_category_edit.html', 'id': '', 'action': '/api/categories'}


@get('/manage/categories/edit')
def manage_edit_categories(*, id):
    return {'__template__': 'manage_category_edit.html', 'id': id, 'action': '/api/categories/{}'.format(id)}
