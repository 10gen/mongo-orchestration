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
from lib.shards import Shards
from bottle import route, request, response, run


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


def _sh_create(params):
    cluster_id = Shards().create(params)
    result = Shards().info(cluster_id)
    return send_result(200, result)


def _build_server_uris(docs):
    return [{'uri': '/servers/' + doc['id']} for doc in docs]


def _build_shard_info(shard_docs):
    resource_info = []
    for shard_doc in shard_docs:
        repl_set = shard_doc.get('isReplicaSet')
        resource = 'replica_sets' if repl_set else 'servers'
        info = {
            "shard_id": shard_doc['id'],
            "tags": shard_doc['tags'],
            "uri": '/' + resource + '/' + shard_doc['_id']}
        info['isReplicaSet' if repl_set else 'isServer'] = True
        resource_info.append(info)
    return resource_info


@error_wrap
def sh_create():
    logger.debug("sh_create()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    data = preset_merge(data, 'sharded_clusters')
    return _sh_create(data)


@error_wrap
def sh_list():
    logger.debug("sh_list()")
    data = [sh_info for sh_info in Shards()]
    return send_result(200, data)


@error_wrap
def info(cluster_id):
    logger.debug("info({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = Shards().info(cluster_id)
    return send_result(200, result)


@error_wrap
def sh_create_by_id(cluster_id):
    logger.debug("sh_create()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    data = preset_merge(data, 'sharded_clusters')
    data['id'] = cluster_id
    return _sh_create(data)


@error_wrap
def sh_del(cluster_id):
    logger.debug("sh_del({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = Shards().remove(cluster_id)
    return send_result(204, result)


@error_wrap
def shard_add(cluster_id):
    logger.debug("shard_add({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    result = Shards().member_add(cluster_id, data)
    return send_result(200, result)


@error_wrap
def shards(cluster_id):
    logger.debug("shards({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    members = Shards().members(cluster_id)
    return send_result(200, _build_shard_info(members))


@error_wrap
def configservers(cluster_id):
    logger.debug("configservers({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = _build_server_uris(Shards().configservers(cluster_id))
    return send_result(200, result)


@error_wrap
def routers(cluster_id):
    logger.debug("routers({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = _build_server_uris(Shards().routers(cluster_id))
    return send_result(200, result)


@error_wrap
def router_add(cluster_id):
    logger.debug("router_add({cluster_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    result = Shards().router_add(cluster_id, data)
    return send_result(200, result)


@error_wrap
def router_del(cluster_id, router_id):
    logger.debug("router_del({cluster_id}), {router_id}".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = Shards().router_del(cluster_id, router_id)
    return send_result(200, result)


@error_wrap
def shard_info(cluster_id, shard_id):
    logger.debug("shard_info({cluster_id}, {shard_id})".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = Shards().member_info(cluster_id, shard_id)
    return send_result(200, result)


@error_wrap
def shard_del(cluster_id, shard_id):
    logger.debug("member_del({cluster_id}), {shard_id}".format(**locals()))
    if cluster_id not in Shards():
        return send_result(404)
    result = Shards().member_del(cluster_id, shard_id)
    return send_result(200, result)


ROUTES = {
    Route('/sharded_clusters', method='POST'): sh_create,
    Route('/sharded_clusters', method='GET'): sh_list,
    Route('/sharded_clusters/<cluster_id>', method='GET'): info,
    Route('/sharded_clusters/<cluster_id>', method='PUT'): sh_create_by_id,
    Route('/sharded_clusters/<cluster_id>', method='DELETE'): sh_del,
    Route('/sharded_clusters/<cluster_id>/shards', method='POST'): shard_add,
    Route('/sharded_clusters/<cluster_id>/shards', method='GET'): shards,
    Route('/sharded_clusters/<cluster_id>/configservers',
          method='GET'): configservers,
    Route('/sharded_clusters/<cluster_id>/routers', method='GET'): routers,
    Route('/sharded_clusters/<cluster_id>/routers', method='POST'): router_add,
    Route('/sharded_clusters/<cluster_id>/routers/<router_id>',
          method='DELETE'): router_del,
    Route('/sharded_clusters/<cluster_id>/shards/<shard_id>',
          method='GET'): shard_info,
    Route('/sharded_clusters/<cluster_id>/shards/<shard_id>',
          method='DELETE'): shard_del
}

setup_versioned_routes(ROUTES, version='v1')
# Assume v1 if no version is specified.
setup_versioned_routes(ROUTES)

if __name__ == '__main__':
    rs = Shards()
    rs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
