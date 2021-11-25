#!/usr/bin/env python3
# -*- coding: utf-8 -*-


'''
JSON API definition.
'''

import json, inspect, functools
from config import configs

class APIError(Exception):
    '''
    the base APIError which contains error(required), data(optional) and message(optional).
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The data specifies the error field of input form.
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)


class Page(object):

    def __init__(self, item_count, page_index=1, page_size=configs.page_size, page_show=configs.page_show):
        self.item_count = item_count
        self.page_show = page_show - 2 # remomve first and last page.
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_prev = self.page_index > 1
        self.pagelist()


    def __str__(self):
        return 'item_count: {}, page_count: {}, page_index: {}, page_size: {}, page_show: {}, offset: {}, limit: {}'.format(self.item_count, self.page_count, self.page_index, self.page_size, self.page_show, self.offset, self.limit)

    __repr__ = __str__

    def pagelist(self):
        left = 2
        right = self.page_count

        if self.page_count - 2 > self.page_show:
            left = self.page_index - self.page_show // 2
            if left < 2:
                left = 2
            right = left + self.page_show
            if right > self.page_count:
                right = self.page_count
                left = right - self.page_show

        self.page_list = list(range(left, right))