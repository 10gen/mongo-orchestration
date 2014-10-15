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
import tempfile

from uuid import uuid4

from mongo_orchestration.container import Container
from mongo_orchestration.errors import ShardedClusterError
from mongo_orchestration.servers import Servers
from mongo_orchestration.replica_sets import ReplicaSets
from mongo_orchestration.singleton import Singleton
from pymongo import MongoClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ShardedCluster(object):
    """class represents Sharding configuration"""

    def __init__(self, params):
        """init configuration acording params"""
        self.id = params.get('id', None) or str(uuid4())
        self.login = params.get('login', '')
        self.password = params.get('password', '')
        self.auth_key = params.get('auth_key', None)
        self._version = params.get('version')
        self._configsvrs = []
        self._routers = []
        self._shards = {}
        self.tags = {}

        self.sslParams = params.get('sslParams', {})
        self.kwargs = {}

        if not not self.sslParams:
            self.kwargs['ssl'] = True

        self.__init_configsvr(params.get('configsvrs', [{}]))
        for r in params.get('routers', [{}]):
            self.router_add(r)
        for cfg in params.get('shards', []):
            shard_params = cfg.get('shardParams', {})
            shard_tags = shard_params.pop('tags', None)
            info = self.member_add(cfg.get('id', None), shard_params)
            if shard_tags:
                self.tags[info['id']] = shard_tags

        if self.tags:
            for sh_id in self.tags:
                logger.debug('Add tags %r to %s' % (self.tags[sh_id], sh_id))
                self.connection().config.shards.update(
                    {'_id': sh_id},
                    {'$addToSet': {'$each': self.tags[sh_id]}})

        if self.login:
            client = MongoClient(self.router['hostname'], **self.kwargs)
            client.admin.add_user(self.login, self.password,
                                  roles=['__system',
                                         'clusterAdmin',
                                         'dbAdminAnyDatabase',
                                         'readWriteAnyDatabase',
                                         'userAdminAnyDatabase'])

    def __init_configsvr(self, params):
        """create and start config servers"""
        self._configsvrs = []
        for cfg in params:
            cfg.update({'configsvr': True})
            self._configsvrs.append(Servers().create(
                'mongod', cfg,
                sslParams=self.sslParams, autostart=True,
                auth_key=self.auth_key, version=self._version))

    def __len__(self):
        return len(self._shards)

    @property
    def configsvrs(self):
        """return list of config servers"""
        return [{'id': h_id, 'hostname': Servers().hostname(h_id)} for h_id in self._configsvrs]

    @property
    def routers(self):
        """return list of routers"""
        return [{'id': h_id, 'hostname': Servers().hostname(h_id)} for h_id in self._routers]

    @property
    def members(self):
        """return list of members"""
        # return [{'id': shard, 'hostname': Servers().hostname(info['_id'])} for shard, info in self._shards.items()]
        return [self.member_info(item) for item in self._shards]

    @property
    def router(self):
        """return first available router"""
        for server in self._routers:
            info = Servers().info(server)
            if info['procInfo'].get('alive', False):
                return {'id': server, 'hostname': Servers().hostname(server)}

    def router_add(self, params):
        """add new router (mongos) into existing configuration"""
        cfgs = ','.join([Servers().info(item)['uri'] for item in self._configsvrs])
        params.update({'configdb': cfgs})
        self._routers.append(Servers().create(
            'mongos', params, sslParams=self.sslParams, autostart=True,
            auth_key=self.auth_key, version=self._version))
        return {'id': self._routers[-1], 'hostname': Servers().hostname(self._routers[-1])}

    def connection(self):
        c = MongoClient(self.router['hostname'], **self.kwargs)
        try:
            self.login and self.password and c.admin.authenticate(self.login, self.password)
        except:
            pass
        return c

    def router_command(self, command, arg=None, is_eval=False):
        """run command on the router server

        Args:
            command - command string
            arg - command argument
            is_eval - if True execute command as eval

        return command's result
        """
        mode = is_eval and 'eval' or 'command'

        if isinstance(arg, tuple):
            name, d = arg
        else:
            name, d = arg, {}

        result = getattr(self.connection().admin, mode)(command, name, **d)
        return result

    def router_remove(self, router_id):
        """remove """
        result = Servers().remove(router_id)
        del self._routers[ self._routers.index(router_id) ]
        return { "ok": 1, "routers": self._routers }

    def _add(self, shard_uri, name):
        """execute addShard command"""
        return self.router_command("addShard", (shard_uri, {"name": name}), is_eval=False)

    def member_add(self, member_id=None, params=None):
        """add new member into existing configuration"""
        member_id = member_id or str(uuid4())
        if 'members' in params:
            # is replica set
            rs_params = params.copy()
            rs_params.update({'auth_key': self.auth_key})
            rs_params.update({'sslParams': self.sslParams})
            if self.login and self.password:
                rs_params.update({'login': self.login, 'password': self.password})
            if self._version:
                rs_params['version'] = self._version
            rs_id = ReplicaSets().create(rs_params)
            members = ReplicaSets().members(rs_id)
            cfgs = rs_id + r"/" + ','.join([item['host'] for item in members])
            result = self._add(cfgs, member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isReplicaSet': True, '_id': rs_id}
                # return self._shards[result['shardAdded']].copy()
                return self.member_info(member_id)

        else:
            # is single server
            params.update({'autostart': True, 'auth_key': self.auth_key, 'sslParams': self.sslParams})
            params['procParams'] = params.get('procParams', {})
            if self._version:
                params['version'] = self._version
            logger.debug("servers create params: {params}".format(**locals()))
            server_id = Servers().create('mongod', **params)
            result = self._add(Servers().info(server_id)['uri'], member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isServer': True, '_id': server_id}
                # return self._shards[result['shardAdded']]
                return self.member_info(member_id)

    def member_info(self, member_id):
        """return info about member"""
        info = self._shards[member_id].copy()
        info['id'] = member_id
        info['tags'] = self.tags.get(member_id, list())
        return info

    def _remove(self, shard_name):
        """remove member from configuration"""
        result = self.router_command("removeShard", shard_name, is_eval=False)
        if result['ok'] == 1 and result['state'] == 'completed':
            shard = self._shards.pop(shard_name)
            if shard.get('isServer', False):
                Servers().remove(shard['_id'])
            if shard.get('isReplicaSet', False):
                ReplicaSets().remove(shard['_id'])
        return result

    def member_remove(self, member_id):
        """remove member from configuration"""
        return self._remove(member_id)

    def reset(self):
        """Ensure all shards, configs, and routers are running and available."""
        # Ensure all shards by calling "reset" on each.
        for shard_id in self._shards:
            if self._shards[shard_id].get('isReplicaSet'):
                singleton = ReplicaSets()
            elif self._shards[shard_id].get('isServer'):
                singleton = Servers()
            singleton.command(self._shards[shard_id]['_id'], 'reset')
        # Ensure all config servers by calling "reset" on each.
        for config_id in self._configsvrs:
            Servers().command(config_id, 'reset')
        # Ensure all routers by calling "reset" on each.
        for router_id in self._routers:
            Servers().command(router_id, 'reset')
        return self.info()

    def info(self):
        """return info about configuration"""
        uri = ','.join(x['hostname'] for x in self.routers)
        mongodb_uri = 'mongodb://' + uri
        return {'id': self.id,
                'shards': self.members,
                'configsvrs': self.configsvrs,
                'routers': self.routers,
                'uri': uri,
                'mongodb_uri': mongodb_uri,
                'orchestration': 'sharded_clusters'}

    def cleanup(self):
        """cleanup configuration: stop and remove all servers"""
        for _id, shard in self._shards.items():
            if shard.get('isServer', False):
                Servers().remove(shard['_id'])
            if shard.get('isReplicaSet', False):
                ReplicaSets().remove(shard['_id'])

        for mongos in self._routers:
            Servers().remove(mongos)

        for configsvr in self._configsvrs:
            Servers().remove(configsvr)

        self._configsvrs = []
        self._routers = []
        self._shards = {}


class ShardedClusters(Singleton, Container):
    """ ShardedClusters is a dict-like collection for ShardedCluster objects"""
    _name = 'shards'
    _obj_type = ShardedCluster
    releases = {}
    pids_file = tempfile.mktemp(prefix="mongo-")

    def set_settings(self, releases=None, default_release=None):
        """set path to storage"""
        super(ShardedClusters, self).set_settings(releases, default_release)
        ReplicaSets().set_settings(releases, default_release)

    def __getitem__(self, key):
        return self.info(key)

    def cleanup(self):
        """remove all servers with their data"""
        for server in self:
            self.remove(server)

    def create(self, params):
        """create new ShardedCluster
        Args:
           params - dictionary with specific params for instance
        Return cluster_id
           where cluster_id - id which can use to take the cluster from servers collection
        """
        sh_id = params.get('id', str(uuid4()))
        if sh_id in self:
            raise ShardedClusterError(
                "Sharded cluster with id %s already exists." % sh_id)
        params['id'] = sh_id
        cluster = ShardedCluster(params)
        self[cluster.id] = cluster
        return cluster.id

    def remove(self, cluster_id):
        """remove cluster and data stuff
        Args:
            cluster_id - cluster identity
        """
        cluster = self._storage.pop(cluster_id)
        cluster.cleanup()

    def info(self, cluster_id):
        """return dictionary object with info about cluster
        Args:
            cluster_id - cluster identity
        """
        return self._storage[cluster_id].info()

    def configsvrs(self, cluster_id):
        """return list of config servers"""
        return self._storage[cluster_id].configsvrs

    def routers(self, cluster_id):
        """return list of routers"""
        return self._storage[cluster_id].routers

    def router_add(self, cluster_id, params):
        """add new router"""
        cluster = self._storage[cluster_id]
        result = cluster.router_add(params)
        self._storage[cluster_id] = cluster
        return result

    def router_del(self, cluster_id, router_id):
        """remove router from the ShardedCluster"""
        cluster = self._storage[cluster_id]
        result = cluster.router_remove(router_id)
        self._storage[cluster_id] = cluster
        return result

    def members(self, cluster_id):
        """return list of members"""
        return self._storage[cluster_id].members

    def member_info(self, cluster_id, member_id):
        """return info about member"""
        cluster = self._storage[cluster_id]
        return cluster.member_info(member_id)

    def command(self, cluster_id, command, *args):
        """Call a ShardedCluster method."""
        cluster = self._storage[cluster_id]
        try:
            return getattr(cluster, command)(*args)
        except AttributeError:
            raise ValueError("Cannot issue the command %r to ShardedCluster %s"
                             % (command, cluster_id))

    def member_del(self, cluster_id, member_id):
        """remove member from cluster cluster"""
        cluster = self._storage[cluster_id]
        result = cluster.member_remove(member_id)
        self._storage[cluster_id] = cluster
        return result

    def member_add(self, cluster_id, params):
        """add new member into configuration"""
        cluster = self._storage[cluster_id]
        result = cluster.member_add(params.get('id', None), params.get('shardParams', {}))
        self._storage[cluster_id] = cluster
        return result
