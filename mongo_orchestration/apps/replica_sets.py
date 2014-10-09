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
from mongo_orchestration.common import *
from mongo_orchestration.replica_sets import ReplicaSets

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def _rs_create(params):
    rs_id = ReplicaSets().create(params)
    result = ReplicaSets().info(rs_id)
    return send_result(200, result)


def _build_server_info(member_docs):
    server_info = []
    for member_doc in member_docs:
        server_info.append({
            "member_id": member_doc['_id'],
            "uri": '/servers/' + member_doc['server_id']})
    return server_info


@error_wrap
def rs_create():
    logger.debug("rs_create()")
    data = get_json(request.body)
    data = preset_merge(data, 'replica_sets')
    return _rs_create(data)


@error_wrap
def rs_list():
    logger.debug("rs_list()")
    data = [info for info in ReplicaSets()]
    return send_result(200, data)


@error_wrap
def rs_info(rs_id):
    logger.debug("rs_info({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    result = ReplicaSets().info(rs_id)
    return send_result(200, result)


@error_wrap
def rs_command(rs_id):
    logger.debug("rs_command({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    command = get_json(request.body).get('action')
    if command is None:
        raise RequestError('Expected body with an {"action": ...}.')
    result = ReplicaSets().command(rs_id, command)
    return send_result(200, result)


@error_wrap
def rs_create_by_id(rs_id):
    logger.debug("rs_create_by_id()")
    data = get_json(request.body)
    data = preset_merge(data, 'replica_sets')
    data['id'] = rs_id
    return _rs_create(data)


@error_wrap
def rs_del(rs_id):
    logger.debug("rs_del({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    result = ReplicaSets().remove(rs_id)
    return send_result(204, result)


@error_wrap
def member_add(rs_id):
    logger.debug("member_add({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    data = get_json(request.body)
    member_id = ReplicaSets().member_add(rs_id, data)
    result = ReplicaSets().member_info(rs_id, member_id)
    return send_result(200, result)


@error_wrap
def members(rs_id):
    logger.debug("members({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().members(rs_id)))


@error_wrap
def secondaries(rs_id):
    logger.debug("secondaries({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().secondaries(rs_id)))


@error_wrap
def arbiters(rs_id):
    logger.debug("arbiters({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().arbiters(rs_id)))


@error_wrap
def hidden(rs_id):
    logger.debug("hidden({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().hidden(rs_id)))


@error_wrap
def passives(rs_id):
    logger.debug("passives({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().passives(rs_id)))


@error_wrap
def servers(rs_id):
    logger.debug("hosts({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().servers(rs_id)))


@error_wrap
def rs_member_primary(rs_id):
    logger.debug("rs_member_primary({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info([ReplicaSets().primary(rs_id)])[0])


@error_wrap
def member_info(rs_id, member_id):
    logger.debug("member_info({rs_id}, {member_id})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in ReplicaSets():
        return send_result(404)
    result = ReplicaSets().member_info(rs_id, member_id)
    return send_result(200, result)


@error_wrap
def member_del(rs_id, member_id):
    logger.debug("member_del({rs_id}), {member_id}".format(**locals()))
    member_id = int(member_id)
    if rs_id not in ReplicaSets():
        return send_result(404)
    result = ReplicaSets().member_del(rs_id, member_id)
    return send_result(200, result)


@error_wrap
def member_update(rs_id, member_id):
    logger.debug("member_update({rs_id}, {member_id})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in ReplicaSets():
        return send_result(404)
    data = get_json(request.body)
    ReplicaSets().member_update(rs_id, member_id, data)
    result = ReplicaSets().member_info(rs_id, member_id)
    return send_result(200, result)


ROUTES = {
    Route('/replica_sets', method='POST'): rs_create,
    Route('/replica_sets', method='GET'): rs_list,
    Route('/replica_sets/<rs_id>', method='GET'): rs_info,
    Route('/replica_sets/<rs_id>', method='POST'): rs_command,
    Route('/replica_sets/<rs_id>', method='PUT'): rs_create_by_id,
    Route('/replica_sets/<rs_id>', method='DELETE'): rs_del,
    Route('/replica_sets/<rs_id>/members', method='POST'): member_add,
    Route('/replica_sets/<rs_id>/members', method='GET'): members,
    Route('/replica_sets/<rs_id>/secondaries', method='GET'): secondaries,
    Route('/replica_sets/<rs_id>/arbiters', method='GET'): arbiters,
    Route('/replica_sets/<rs_id>/hidden', method='GET'): hidden,
    Route('/replica_sets/<rs_id>/passives', method='GET'): passives,
    Route('/replica_sets/<rs_id>/servers', method='GET'): servers,
    Route('/replica_sets/<rs_id>/primary', method='GET'): rs_member_primary,
    Route('/replica_sets/<rs_id>/members/<member_id>',
          method='GET'): member_info,
    Route('/replica_sets/<rs_id>/members/<member_id>',
          method='DELETE'): member_del,
    Route('/replica_sets/<rs_id>/members/<member_id>',
          method='PATCH'): member_update
}

setup_versioned_routes(ROUTES, version='v1')
# Assume v1 if no version is specified.
setup_versioned_routes(ROUTES)


if __name__ == '__main__':
    rs = ReplicaSets()
    rs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
