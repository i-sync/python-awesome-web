#!/usr/bin/env python
# _*_ coding: utf-8 _*_

'''
config.py
'''

import config_default

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass