#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import asyncio
import orm
from models import User, Blog, Comment
import logging

loop = asyncio.get_event_loop()

def test():
    yield from orm.create_pool(loop, host='127.0.0.1', port = 3306, user='root', password='123', database='awesome')

    u = User(name='Test', email = 'test@example.com', password = '123', image = 'about:blank')

    yield from u.save()
    #yield from orm.destory_pool()


loop.run_until_complete(test())
loop.close()
