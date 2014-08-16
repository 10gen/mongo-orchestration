#!/usr/bin/python
# coding=utf-8

import errno
import json
import logging
import os


def preset_merge(data, cluster_type):
    preset = data.get('preset', None)
    if preset is not None:
        path = os.path.join('configurations', cluster_type, preset)
        preset_data = {}
        with open (path, "r") as preset_file:
            preset_data = json.loads(preset_file.read())
        data = dict(preset_data.items() + data.items())
        print("preset_merge preset:{preset} path:{path} preset_data:{preset_data} data:{data}".format(
            preset = preset, path = path, preset_data = preset_data, data = data))
    return data
