#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
config.py
'''

#import config_default
import os
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
    for k, v in override.items():
        if k not in r:
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
with open('{}/config.json'.format(path), encoding='utf-8') as f:
    configs = json.load(f)

with open('{}/user.json'.format(path), encoding='utf-8') as f:
    user = json.load(f)

configs = merge(configs, user)

database = configs.get('database', {})

env_engine = os.getenv('DATABASE_ENGINE')
if env_engine:
    database['engine'] = env_engine

env_dsn = os.getenv('DATABASE_DSN')
if env_dsn:
    database['dsn'] = env_dsn
    database['engine'] = 'postgresql'

env_mapping = {
    'DB_HOST': 'host',
    'DB_PORT': 'port',
    'DB_USER': 'user',
    'DB_PASSWORD': 'password',
    'DB_NAME': 'database',
    'PGHOST': 'host',
    'PGPORT': 'port',
    'PGUSER': 'user',
    'PGPASSWORD': 'password',
    'PGDATABASE': 'database',
}
for env_name, config_key in env_mapping.items():
    value = os.getenv(env_name)
    if value is None:
        continue
    if config_key == 'port':
        try:
            value = int(value)
        except ValueError:
            continue
    database[config_key] = value

configs['database'] = database

configs = toDict(configs)
