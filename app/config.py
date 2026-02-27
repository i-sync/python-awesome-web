#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import json
import os
from pathlib import Path


class Dict(dict):
    """Simple dict with x.y style access."""

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
    result = {}
    for key, value in defaults.items():
        if key in override:
            if isinstance(value, dict):
                result[key] = merge(value, override[key])
            else:
                result[key] = override[key]
        else:
            result[key] = value
    for key, value in override.items():
        if key not in result:
            result[key] = value
    return result


def to_dict(value):
    result = Dict()
    for key, item in value.items():
        result[key] = to_dict(item) if isinstance(item, dict) else item
    return result


def _load_json(path):
    with open(path, encoding='utf-8') as fp:
        return json.load(fp)


_default_config_dir = Path(__file__).resolve().parents[1] / 'www' / 'config'
config_dir = Path(os.getenv('APP_CONFIG_DIR', str(_default_config_dir)))

configs = _load_json(config_dir / 'config.json')
user = _load_json(config_dir / 'user.json')
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
configs = to_dict(configs)
