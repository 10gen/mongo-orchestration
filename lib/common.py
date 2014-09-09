#!/usr/bin/python
# coding=utf-8

import collections
import json
import os
import copy


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def preset_merge(data, cluster_type):
    preset = data.get('preset', None)
    if preset is not None:
        path = os.path.join('configurations', cluster_type, preset)
        preset_data = {}
        with open(path, "r") as preset_file:
            preset_data = json.loads(preset_file.read())
        data = update(copy.deepcopy(preset_data), data)
    return data
