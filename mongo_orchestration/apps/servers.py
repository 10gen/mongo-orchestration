#!/usr/bin/python
# coding=utf-8
# Copyright 2012-2014 MongoDB, Inc.
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

import logging
import sys

from bottle import request, run

sys.path.insert(0, '..')

from mongo_orchestration.apps import (error_wrap, get_json, Route,
                                      send_result, setup_versioned_routes)
from mongo_orchestration.apps.links import base_link, server_link
from mongo_orchestration.common import *
from mongo_orchestration.errors import RequestError
from mongo_orchestration.servers import Servers

logger = logging.getLogger(__name__)


__version__ = '0.9'


def _host_create(params):
    host_id = params.get('id')
    host_id = Servers().create(params['name'],
                               params.get('procParams', {}),
                               params.get('sslParams', {}),
                               params.get('auth_key', ''),
                               params.get('login', ''),
                               params.get('password', ''),
                               params.get('timeout', 300),
                               params.get('autostart', True),
                               host_id,
                               params.get('version', ''))
    result = Servers().info(host_id)
    server_id = result['id']
    result['links'] = [
        server_link(rel, server_id)
        for rel in ('delete-server', 'get-server-info', 'server-command')
    ]
    return result


@error_wrap
def base_uri():
    logger.debug("base_uri()")
    data = {
        "service": "mongo-orchestration",
        "version": __version__,
        "links": [
            server_link('get-servers'),
            server_link('add-server'),
            base_link('get-releases'),
            base_link('service', rel_self=True)
        ]
    }
    return send_result(200, data)


@error_wrap
def releases_list():
    response = {
        'releases': Servers().releases,
        'links': [
            base_link('get-releases', rel_self=True),
            base_link('service')
        ]
    }
    return send_result(200, response)


@error_wrap
def host_create():
    data = get_json(request.body)
    data = preset_merge(data, 'servers')
    result = {'server': _host_create(data)}
    result['server']['links'].append(server_link('add-server', rel_self=True))
    result['links'] = [
        server_link('get-servers'),
        base_link('get-releases'),
        base_link('service')
    ]
    return send_result(200, result)


@error_wrap
def host_list():
    logger.debug("host_list()")
    servers = []
    for server_id in Servers():
        server_info = {'id': server_id}
        server_info['links'] = [
            server_link(rel, server_id)
            for rel in ('delete-server', 'get-server-info', 'server-command')
        ]
        servers.append(server_info)
    response = {'links': [
        server_link('add-server'),
        server_link('get-servers', rel_self=True),
        base_link('get-releases'),
        base_link('service')
    ]}
    response['servers'] = servers
    return send_result(200, response)


@error_wrap
def host_info(host_id):
    logger.debug("host_info({host_id})".format(**locals()))
    if host_id not in Servers():
        return send_result(404)
    result = Servers().info(host_id)
    result['links'] = [
        server_link('delete-server', host_id),
        server_link('get-server-info', host_id, rel_self=True),
        server_link('server-command', host_id)
    ]
    return send_result(200, result)


@error_wrap
def host_create_by_id(host_id):
    data = get_json(request.body)
    data = preset_merge(data, 'servers')
    data['id'] = host_id
    result = {'server': _host_create(data)}
    result['server']['links'].append(
        server_link('add-server-by-id', host_id, rel_self=True)
    )
    return send_result(200, result)


@error_wrap
def host_del(host_id):
    logger.debug("host_del({host_id})")
    if host_id not in Servers():
        return send_result(404)
    Servers().remove(host_id)
    return send_result(204)


@error_wrap
def host_command(host_id):
    logger.debug("host_command({host_id})".format(**locals()))
    if host_id not in Servers():
        return send_result(404)
    command = get_json(request.body).get('action')
    if command is None:
        raise RequestError('Expected body with an {"action": ...}.')
    result = {
        'command_result': Servers().command(host_id, command),
        'links': [
            server_link('delete-server', host_id),
            server_link('get-server-info', host_id),
            server_link('server-command', host_id, rel_self=True)
        ]
    }
    return send_result(200, result)


ROUTES = {
    Route('/', method='GET'): base_uri,
    Route('/releases', method='GET'): releases_list,
    Route('/servers', method='POST'): host_create,
    Route('/servers', method='GET'): host_list,
    Route('/servers/<host_id>', method='GET'): host_info,
    Route('/servers/<host_id>', method='PUT'): host_create_by_id,
    Route('/servers/<host_id>', method='DELETE'): host_del,
    Route('/servers/<host_id>', method='POST'): host_command
}

setup_versioned_routes(ROUTES, version='v1')
# Assume v1 if no version is specified.
setup_versioned_routes(ROUTES)

if __name__ == '__main__':
    hs = Servers()
    hs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
