#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import traceback
import sys

sys.path.insert(0, '..')
from apps import setup_versioned_routes, Route
from lib.common import *
from lib.replica_sets import ReplicaSets
from bottle import request, response, run


def send_result(code, result=None):
    logger.debug("send_result({code}, {result})".format(**locals()))
    content = None
    response.content_type = None
    if result is not None:
        content = json.dumps(result)
        response.content_type = "application/json"
    response.status = code
    return content


def error_wrap(f):
    def wrap(*arg, **kwd):
        f_name = f.func_name
        logger.debug("{f_name}({arg}, {kwd})".format(f_name=f_name, arg=arg, kwd=kwd))
        try:
            return f(*arg, **kwd)
        except StandardError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            logger.error("Exception {exc_type} {exc_value} while {f_name}".format(**locals()))
            logger.error(err_message)
            return send_result(500, err_message)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            logger.critical("Exception {exc_type} {exc_value} while {f_name}".format(**locals()))
            logger.critical(err_message)
            return send_result(500, err_message)

    return wrap


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
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
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
def rs_create_by_id(rs_id):
    logger.debug("rs_create_by_id()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
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
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
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
def hosts(rs_id):
    logger.debug("hosts({rs_id})".format(**locals()))
    if rs_id not in ReplicaSets():
        return send_result(404)
    return send_result(200, _build_server_info(ReplicaSets().hosts(rs_id)))


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
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    ReplicaSets().member_update(rs_id, member_id, data)
    result = ReplicaSets().member_info(rs_id, member_id)
    return send_result(200, result)


ROUTES = {
    Route('/replica_sets', method='POST'): rs_create,
    Route('/replica_sets', method='GET'): rs_list,
    Route('/replica_sets/<rs_id>', method='GET'): rs_info,
    Route('/replica_sets/<rs_id>', method='PUT'): rs_create_by_id,
    Route('/replica_sets/<rs_id>', method='DELETE'): rs_del,
    Route('/replica_sets/<rs_id>/members', method='POST'): member_add,
    Route('/replica_sets/<rs_id>/members', method='GET'): members,
    Route('/replica_sets/<rs_id>/secondaries', method='GET'): secondaries,
    Route('/replica_sets/<rs_id>/arbiters', method='GET'): arbiters,
    Route('/replica_sets/<rs_id>/hidden', method='GET'): hidden,
    Route('/replica_sets/<rs_id>/passives', method='GET'): passives,
    Route('/replica_sets/<rs_id>/hosts', method='GET'): hosts,
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
