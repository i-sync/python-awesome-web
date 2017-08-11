#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
config.py
'''

#import config_default
import os.path
import json

class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kwargs):
        super(Dict, self).__init__(**kwargs)

        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '{}'".format(key))

    def __setattr__(self, key, value):
        self[key] = value


def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v

    return r

def toDict(d):
    D = Dict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D


path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')

configs = None
user = None
with open('{}/config.json'.format(path)) as f:
    configs = json.load(f)

with open('{}/user.json'.format(path)) as f:
    user = json.load(f)

configs = merge(configs, user)

configs = toDict(configs)