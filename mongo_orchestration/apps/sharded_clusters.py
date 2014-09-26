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
from mongo_orchestration.apps.links import (
    sharded_cluster_link, all_replica_set_links, all_server_links,
    all_sharded_cluster_links, all_base_links)
from mongo_orchestration.common import *
from mongo_orchestration.sharded_clusters import ShardedClusters

logger = logging.getLogger(__name__)


def _sh_create(params):
    cluster_id = ShardedClusters().create(params)
    result = ShardedClusters().info(cluster_id)
    result['links'] = all_sharded_cluster_links(cluster_id)
    return result


@error_wrap
def sh_create():
    logger.debug("sh_create()")
    data = get_json(request.body)
    data = preset_merge(data, 'sharded_clusters')
    result = {'sharded_cluster': _sh_create(data)}
    result['links'] = all_base_links('add-sharded-cluster')
    return send_result(200, result)


@error_wrap
def sh_list():
    logger.debug("sh_list()")
    sharded_clusters = []
    for cluster_id in ShardedClusters():
        cluster_info = {'id': cluster_id}
        cluster_info['links'] = all_sharded_cluster_links(
            cluster_id, rel_to='get-sharded-clusters')
        sharded_clusters.append(cluster_info)
    response = {'links': all_base_links('get-sharded-clusters')}
    response['sharded_clusters'] = sharded_clusters
    return send_result(200, response)


@error_wrap
def info(cluster_id):
    logger.debug("info({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    result = ShardedClusters().info(cluster_id)
    result['links'] = all_sharded_cluster_links(
        cluster_id, rel_to='get-sharded-cluster-info')
    return send_result(200, result)


@error_wrap
def sh_command(cluster_id):
    logger.debug("sh_command({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    command = get_json(request.body).get('action')
    if command is None:
        raise RequestError('Expected body with an {"action": ...}.')
    result = {
        'command_result': ShardedClusters().command(cluster_id, command),
        'links': all_sharded_cluster_links(cluster_id,
                                           rel_to='sharded-cluster-command')
    }
    return send_result(200, result)


@error_wrap
def sh_create_by_id(cluster_id):
    logger.debug("sh_create()")
    data = get_json(request.body)
    data = preset_merge(data, 'sharded_clusters')
    data['id'] = cluster_id
    result = {'sharded_cluster': _sh_create(data)}
    result['sharded_cluster']['links'].append(
        sharded_cluster_link('add-sharded-cluster-by-id',
                             cluster_id, self_rel=True)
    )
    result['links'] = all_base_links()
    return send_result(200, result)


@error_wrap
def sh_del(cluster_id):
    logger.debug("sh_del({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    result = ShardedClusters().remove(cluster_id)
    return send_result(204, result)


@error_wrap
def shard_add(cluster_id):
    logger.debug("shard_add({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    data = get_json(request.body)
    shard_info = ShardedClusters().member_add(cluster_id, data)
    result = {'shard': shard_info}
    result['shard']['links'] = _build_shard_links(cluster_id, shard_info)
    result['links'] = all_sharded_cluster_links(cluster_id)
    return send_result(200, result)


@error_wrap
def shards(cluster_id):
    logger.debug("shards({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    shard_docs = []
    for shard_info in ShardedClusters().members(cluster_id):
        shard_id = shard_info['id']
        resource_id = shard_info['_id']
        links = [
            sharded_cluster_link(rel, cluster_id, shard_id=shard_id)
            for rel in ('add-shard', 'delete-shard', 'get-shard-info')
        ]
        if shard_info.get('isReplicaSet'):
            links.extend(all_replica_set_links(resource_id))
        else:
            links.extend(all_server_links(resource_id))
        shard_info['links'] = links
        shard_docs.append(shard_info)
    result = {
        'shards': shard_docs,
        'links': all_sharded_cluster_links(cluster_id, rel_to='get-shards')
    }
    return send_result(200, result)


@error_wrap
def configsvrs(cluster_id):
    logger.debug("configsvrs({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    config_docs = []
    for config_info in ShardedClusters().configsvrs(cluster_id):
        server_id = config_info['id']
        config_info['links'] = all_server_links(server_id)
        config_docs.append(config_info)
    result = {
        'configsvrs': config_docs,
        'links': all_sharded_cluster_links(cluster_id,
                                           rel_to='get-configsvrs')
    }
    return send_result(200, result)


@error_wrap
def routers(cluster_id):
    logger.debug("routers({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    router_docs = []
    for router_info in ShardedClusters().routers(cluster_id):
        # Server id is the same as router id.
        server_id = router_info['id']
        links = [
            sharded_cluster_link('delete-router',
                                 cluster_id, router_id=server_id)
        ]
        links.extend(all_server_links(server_id))
        router_info['links'] = links
        router_docs.append(router_info)
    result = {
        'routers': router_docs,
        'links': all_sharded_cluster_links(cluster_id,
                                           rel_to='get-routers')
    }
    return send_result(200, result)


@error_wrap
def router_add(cluster_id):
    logger.debug("router_add({cluster_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    data = get_json(request.body)
    router_info = ShardedClusters().router_add(cluster_id, data)
    router_id = result['id']
    result = {'router': router_info}
    result['router']['links'] = sharded_cluster_link(
        'delete-router', cluster_id, router_id=router_id)
    result['router']['links'].extend(all_server_links(router_id))
    result['links'] = all_sharded_cluster_links(
        cluster_id, rel_to='add-router')
    return send_result(200, result)


@error_wrap
def router_del(cluster_id, router_id):
    logger.debug("router_del({cluster_id}), {router_id}".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    result = ShardedClusters().router_del(cluster_id, router_id)
    return send_result(204, result)


@error_wrap
def shard_info(cluster_id, shard_id):
    logger.debug("shard_info({cluster_id}, {shard_id})".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    shard_info = ShardedClusters().member_info(cluster_id, shard_id)
    result = {'shard': shard_info}
    links = [
        sharded_cluster_link(rel, cluster_id, shard_id=shard_id)
        for rel in ('add-shard', 'delete-shard', 'get-shard-info')
    ]
    if shard_info.get('isReplicaSet'):
        links.extend(all_replica_set_links(resource_id))
    else:
        links.extend(all_server_links(resource_id))
    result['shard']['links'] = links
    result['links'] = all_sharded_cluster_links(
        cluster_id, rel_to='get-shard-info')
    return send_result(200, result)


@error_wrap
def shard_del(cluster_id, shard_id):
    logger.debug("member_del({cluster_id}), {shard_id}".format(**locals()))
    if cluster_id not in ShardedClusters():
        return send_result(404)
    result = ShardedClusters().member_del(cluster_id, shard_id)
    return send_result(204, result)


ROUTES = {
    Route('/sharded_clusters', method='POST'): sh_create,
    Route('/sharded_clusters', method='GET'): sh_list,
    Route('/sharded_clusters/<cluster_id>', method='GET'): info,
    Route('/sharded_clusters/<cluster_id>', method='POST'): sh_command,
    Route('/sharded_clusters/<cluster_id>', method='PUT'): sh_create_by_id,
    Route('/sharded_clusters/<cluster_id>', method='DELETE'): sh_del,
    Route('/sharded_clusters/<cluster_id>/shards', method='POST'): shard_add,
    Route('/sharded_clusters/<cluster_id>/shards', method='GET'): shards,
    Route('/sharded_clusters/<cluster_id>/configsvrs',
          method='GET'): configsvrs,
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
    rs = ShardedClusters()
    rs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
