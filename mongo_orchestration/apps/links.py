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
"""Utilities for building links for discoverable API."""


_BASE_LINKS = {
    'get-releases': {'rel': 'get-releases', 'href': '/v1/releases',
                     'method': 'GET'},
    'service': {'rel': 'service', 'href': '/v1', 'method': 'GET'}
}
_SERVER_LINKS = {
    'get-servers': {'method': 'GET', 'href': '{servers_href}'},
    'add-server': {'method': 'POST', 'href': '{servers_href}'},
    'add-server-by-id': {'method': 'PUT', 'href': '{servers_href}/{server_id}'},
    'delete-server': {'method': 'DELETE', 'href': '{servers_href}/{server_id}'},
    'get-server-info': {'method': 'GET', 'href': '{servers_href}/{server_id}'},
    'server-command': {'method': 'POST', 'href': '{servers_href}/{server_id}',
                       'template': {'action': "<action name>"},
                       'actions': ['start', 'stop', 'restart', 'freeze',
                                   'stepdown', 'reset']}
}
_REPLICA_SET_LINKS = {
    'get-replica-set-info': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}'},
    'get-replica-sets': {'method': 'GET', 'href': '{repls_href}'},
    'add-replica-set': {'method': 'POST', 'href': '{repls_href}'},
    'add-replica-set-by-id': {
        'method': 'PUT', 'href': '{repls_href}/{repl_id}'},
    'delete-replica-set': {
        'href': '{repls_href}/{repl_id}', 'method': 'DELETE'},
    'replica-set-command': {
        'href': '{repls_href}/{repl_id}', 'method': 'POST',
        'actions': ['reset'], 'template': {'action': '<action name>'}},
    'get-replica-set-members': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/members'},
    'add-replica-set-member': {
        'method': 'POST', 'href': '{repls_href}/{repl_id}/members'},
    'delete-replica-set-member': {
        'method': 'DELETE',
        'href': '{repls_href}/{repl_id}/members/{member_id}'},
    'update-replica-set-member-config': {
        'method': 'PATCH',
        'href': '{repls_href}/{repl_id}/members/{member_id}'},
    'get-replica-set-member-info': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/members/{member_id}'},
    'get-replica-set-secondaries': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/secondaries'},
    'get-replica-set-arbiters': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/arbiters'},
    'get-replica-set-hidden-members': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/hidden'},
    'get-replica-set-passive-members': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/passives'},
    'get-replica-set-servers': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/servers'},
    'get-replica-set-primary': {
        'method': 'GET', 'href': '{repls_href}/{repl_id}/primary'},
}
_SHARDED_CLUSTER_LINKS = {
    'add-sharded-cluster': {'method': 'POST', 'href': '{clusters_href}'},
    'get-sharded-clusters': {'method': 'GET', 'href': '{clusters_href}'},
    'get-sharded-cluster-info': {
        'method': 'GET', 'href': '{clusters_href}/{cluster_id}'},
    'sharded-cluster-command': {
        'method': 'POST', 'href': '{clusters_href}/{cluster_id}'},
    'add-sharded-cluster-by-id': {
        'method': 'PUT', 'href': '{clusters_href}/{cluster_id}'},
    'delete-sharded-cluster': {
        'method': 'DELETE', 'href': '{clusters_href}/{cluster_id}'},
    'add-shard': {
        'method': 'POST', 'href': '{clusters_href}/{cluster_id}/shards'},
    'get-shards': {
        'method': 'GET', 'href': '{clusters_href}/{cluster_id}/shards'},
    'get-configsvrs': {
        'method': 'GET', 'href': '{clusters_href}/{cluster_id}/configsvrs'},
    'get-routers': {
        'method': 'GET', 'href': '{clusters_href}/{cluster_id}/routers'},
    'add-router': {
        'method': 'POST', 'href': '{clusters_href}/{cluster_id}/routers'},
    'delete-router': {
        'method': 'DELETE',
        'href': '{clusters_href}/{cluster_id}/routers/{router_id}'},
    'get-shard-info': {
        'method': 'GET',
        'href': '{clusters_href}/{cluster_id}/shards/{shard_id}'},
    'delete-shard': {
        'method': 'DELETE',
        'href': '{clusters_href}/{cluster_id}/shards/{shard_id}'}
}


def base_link(rel, self_rel=False):
    """Helper for getting a link document under the API root, given a rel."""
    link = _BASE_LINKS[rel].copy()
    link['rel'] = 'self' if self_rel else rel
    return link


def all_base_links(rel_to=None):
    """Get a list of all links to be included to base (/) API requests."""
    links = [
        base_link('get-releases'),
        base_link('service'),
        server_link('get-servers'),
        server_link('add-server'),
        replica_set_link('add-replica-set'),
        replica_set_link('get-replica-sets'),
        sharded_cluster_link('add-sharded-cluster'),
        sharded_cluster_link('get-sharded-clusters')
    ]
    for link in links:
        if link['rel'] == rel_to:
            link['rel'] = 'self'
    return links


def server_link(rel, server_id=None, self_rel=False):
    """Helper for getting a Server link document, given a rel."""
    servers_href = '/v1/servers'
    link = _SERVER_LINKS[rel].copy()
    link['href'] = link['href'].format(**locals())
    link['rel'] = 'self' if self_rel else rel
    return link


def all_server_links(server_id, rel_to=None):
    """Get a list of all links to be included with Servers."""
    return [
        server_link(rel, server_id, self_rel=(rel == rel_to))
        for rel in ('delete-server', 'get-server-info', 'server-command')
    ]


def replica_set_link(rel, repl_id=None, member_id=None, self_rel=False):
    """Helper for getting a ReplicaSet link document, given a rel."""
    repls_href = '/v1/replica_sets'
    link = _REPLICA_SET_LINKS[rel].copy()
    link['href'] = link['href'].format(**locals())
    link['rel'] = 'self' if self_rel else rel
    return link


def all_replica_set_links(rs_id, rel_to=None):
    """Get a list of all links to be included with replica sets."""
    return [
        replica_set_link(rel, rs_id, self_rel=(rel == rel_to))
        for rel in (
            'get-replica-set-info',
            'delete-replica-set', 'replica-set-command',
            'get-replica-set-members', 'add-replica-set-member',
            'get-replica-set-secondaries', 'get-replica-set-primary',
            'get-replica-set-arbiters', 'get-replica-set-hidden-members',
            'get-replica-set-passive-members', 'get-replica-set-servers'
        )
    ]


def sharded_cluster_link(rel, cluster_id=None,
                         shard_id=None, router_id=None, self_rel=False):
    """Helper for getting a ShardedCluster link document, given a rel."""
    clusters_href = '/v1/sharded_clusters'
    link = _SHARDED_CLUSTER_LINKS[rel].copy()
    link['href'] = link['href'].format(**locals())
    link['rel'] = 'self' if self_rel else rel
    return link


def all_sharded_cluster_links(cluster_id, shard_id=None,
                              router_id=None, rel_to=None):
    """Get a list of all links to be included with ShardedClusters."""
    return [
        sharded_cluster_link(rel, cluster_id, shard_id, router_id,
                             self_rel=(rel == rel_to))
        for rel in (
            'get-sharded-clusters', 'get-sharded-cluster-info',
            'sharded-cluster-command', 'delete-sharded-cluster',
            'add-shard', 'get-shards', 'get-configsvrs',
            'get-routers', 'add-router'
        )
    ]
