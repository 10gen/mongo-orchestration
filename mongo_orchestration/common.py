#!/usr/bin/python
# coding=utf-8
# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import os
import copy
import json
import stat
import tempfile

DEFAULT_BIND = os.environ.get('MO_HOST', 'localhost')
DEFAULT_PORT = int(os.environ.get('MO_PORT', '8889'))
DEFAULT_SERVER = 'cherrypy'
DEFAULT_AUTH_KEY = os.environ.get('MO_AUTH_KEY', 'auth key')


def create_key_file(auth_key):
    key_file_path = os.path.join(tempfile.mkdtemp(), 'key')
    with open(key_file_path, 'w') as fd:
        fd.write(auth_key)
    os.chmod(key_file_path, stat.S_IRUSR)
    return key_file_path


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
        base_path = os.environ.get("MONGO_ORCHESTRATION_HOME",
                                   os.path.dirname(__file__))
        path = os.path.join(base_path, 'configurations', cluster_type, preset)
        preset_data = {}
        with open(path, "r") as preset_file:
            preset_data = json.loads(preset_file.read())
        data = update(copy.deepcopy(preset_data), data)
    return data
