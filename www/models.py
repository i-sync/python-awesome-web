#!/usr/bin/env python
# _*_ coding: utf-8 _*_


import time
import uuid

from orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
    email = StringField(ddl = 'varchar(50)')
    password = StringField(ddl = 'varchar(50)')
    admin = BooleanField()
    name = StringField(ddl = 'varchar(50)')
    image = StringField(ddl = 'varchar(500)')
    created_at = FloatField(default = time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
    user_id = StringField(ddl = 'varchar(50)')
    user_name = StringField(ddl = 'varchar(50)')
    user_image = StringField(ddl = 'varchar(500)')
    category_id = StringField(ddl = 'varchar(50)')
    category_name = StringField(ddl = 'varchar(50)')
    view_count = IntegerField()
    name = StringField(ddl = 'varchar(50)')
    summary = StringField(ddl = 'varchar(2048)')
    content = TextField()
    created_at = FloatField(default = time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
    blog_id = StringField(ddl = 'varchar(50)')
    user_id = StringField(ddl = 'varchar(50)')
    user_name = StringField(ddl = 'varchar(50)')
    user_image = StringField(ddl = 'varchar(500)')
    content = TextField()
    created_at = FloatField(default = time.time)

class Category(Model):
    __table__ = 'categories'

    id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50')
    name = StringField(ddl = 'varchar(50)')
    created_at = FloatField(default = time.time)

