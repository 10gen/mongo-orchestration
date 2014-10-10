"""Utilities for building links for discoverable API."""


def base_link(rel, self_rel=False):
    """Helper for getting a link document under the API root, given a rel."""
    links = {
        'get-releases': {'rel': 'get-releases', 'href': '/v1/releases',
                         'method': 'GET'},
        'service': {'rel': 'service', 'href': '/v1', 'method': 'GET'}
    }
    link = links[rel]
    link['rel'] = 'self' if self_rel else rel
    return link


def all_base_links(rel_to=None):
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
    base_href = '/v1/servers'
    server_href = '{base_href}/{server_id}'.format(**locals())
    links = {
        'get-servers': {'method': 'GET', 'href': base_href},
        'add-server': {'method': 'POST', 'href': base_href},
        'add-server-by-id': {'method': 'PUT', 'href': server_href},
        'delete-server': {'method': 'DELETE', 'href': server_href},
        'get-server-info': {'method': 'GET', 'href': server_href},
        'server-command': {'method': 'POST', 'href': server_href,
                           'template': {'action': "<action name>"},
                           'actions': ['start', 'stop', 'restart', 'freeze']}
    }
    link = links[rel]
    link['rel'] = 'self' if self_rel else rel
    return link


def all_server_links(server_id, rel_to=None):
    return [
        server_link(rel, server_id, self_rel=(rel == rel_to))
        for rel in ('delete-server', 'get-server-info', 'server-command')
    ]


def replica_set_link(rel, repl_id=None, member_id=None, self_rel=False):
    """Helper for getting a ReplicaSet link document, given a rel."""
    base_href = '/v1/replica_sets'
    repl_href = '{base_href}/{repl_id}'.format(**locals())
    member_href = '{repl_href}/members/{member_id}'.format(**locals())
    links = {
        'get-replica-set-info': {'method': 'GET', 'href': repl_href},
        'get-replica-sets': {'method': 'GET', 'href': base_href},
        'add-replica-set': {'method': 'POST', 'href': base_href},
        'delete-replica-set': {'href': repl_href, 'method': 'DELETE'},
        'replica-set-command': {
            'href': repl_href, 'method': 'POST', 'actions': ['reset'],
            'template': {'action': '<action name>'}},
        'get-replica-set-members': {
            'method': 'GET', 'href': repl_href + '/members'},
        'add-replica-set-member': {
            'method': 'POST', 'href': repl_href + '/members'},
        'delete-replica-set-member': {'method': 'DELETE', 'href': member_href},
        'update-replica-set-member-config': {
            'method': 'PATCH', 'href': member_href},
        'get-replica-set-member-info': {'method': 'GET', 'href': member_href},
        'get-replica-set-secondaries': {
            'method': 'GET', 'href': repl_href + '/secondaries'},
        'get-replica-set-arbiters': {
            'method': 'GET', 'href': repl_href + '/arbiters'},
        'get-replica-set-hidden-members': {
            'method': 'GET', 'href': repl_href + '/hidden'},
        'get-replica-set-passive-members': {
            'method': 'GET', 'href': repl_href + '/passives'},
        'get-replica-set-servers': {
            'method': 'GET', 'href': repl_href + '/servers'},
        'get-replica-set-primary': {
            'method': 'GET', 'href': repl_href + '/primary'},
    }
    link = links[rel]
    link['rel'] = 'self' if self_rel else rel
    return link


def all_replica_set_links(rs_id, rel_to=None):
    # Does not include the rel 'add-replica-set-by-id',
    # since you can't re-add a replica set (given that the id is provided here).
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
    base_href = '/v1/sharded_clusters'
    cluster_href = '{base_href}/{cluster_id}'.format(**locals())
    router_href = '{cluster_href}/routers/{router_id}'.format(**locals())
    shard_href = '{cluster_href}/shards/{shard_id}'.format(**locals())
    links = {
        'add-sharded-cluster': {'method': 'POST', 'href': base_href},
        'get-sharded-clusters': {'method': 'GET', 'href': base_href},
        'get-sharded-cluster-info': {'method': 'GET', 'href': cluster_href},
        'sharded-cluster-command': {'method': 'POST', 'href': cluster_href},
        'add-sharded-cluster-by-id': {'method': 'PUT', 'href': cluster_href},
        'delete-sharded-cluster': {'method': 'DELETE', 'href': cluster_href},
        'add-shard': {'method': 'POST', 'href': cluster_href + '/shards'},
        'get-shards': {'method': 'GET', 'href': cluster_href + '/shards'},
        'get-configsvrs': {'method': 'GET',
                           'href': cluster_href + '/configsvrs'},
        'get-routers': {'method': 'GET', 'href': cluster_href + '/routers'},
        'add-router': {'method': 'POST', 'href': cluster_href + '/routers'},
        'delete-router': {'method': 'DELETE', 'href': router_href},
        'get-shard-info': {'method': 'GET', 'href': shard_href},
        'delete-shard': {'method': 'DELETE', 'href': shard_href}
    }
    link = links[rel]
    link['rel'] = 'self' if self_rel else rel
    return link


def all_sharded_cluster_links(cluster_id, shard_id=None,
                              router_id=None, rel_to=None):
    # Does not include the rel 'add-sharded-cluster-by-id',
    # since you can't re-add a sharded cluster
    # (given that the id is provided here).
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
