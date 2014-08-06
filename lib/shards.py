#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from uuid import uuid4
from lib.singleton import Singleton
from lib.container import Container
import tempfile
from lib.hosts import Hosts
from rs import RS

from pymongo import MongoClient
from pymongo.errors import OperationFailure


class Shard(object):
    """class represents Sharding configuration"""

    def __init__(self, params):
        """init configuration acording params"""
        self.id = params.get('id', None) or 'sh-' + str(uuid4())
        self.login = params.get('login', '')
        self.password = params.get('password', '')
        self.auth_key = params.get('auth_key', None)
        self._configsvrs = []
        self._routers = []
        self._shards = {}
        self.tags = {}

        self.sslParams = params.get('sslParams', {})
        self.kwargs = {}

        if not not self.sslParams:
            self.kwargs['ssl'] = True

        self.__init_configsvr(params.get('configsvrs', [{}]))
        map(self.router_add, params.get('routers', [{}]))
        for cfg in params.get('members', []):
            shard_params = cfg.get('shardParams', {})
            shard_tags = shard_params.pop('tags', None)
            info = self.member_add(cfg.get('id', None), shard_params)
            if shard_tags:
                self.tags[info['id']] = shard_tags

        if self.tags:
            for sh_id in self.tags:
                for tag in self.tags[sh_id]:
                    command = 'sh.addShardTag("{sh_id}", "{tag}")'.format(**locals())
                    logger.debug(command)
                    self.router_command(command=command, is_eval=True)

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
            self._configsvrs.append(Hosts().create('mongod', cfg, sslParams=self.sslParams, autostart=True, auth_key=self.auth_key))

    def __len__(self):
        return len(self._shards)

    @property
    def configsvrs(self):
        """return list of config servers"""
        return [{'id': h_id, 'hostname': Hosts().hostname(h_id)} for h_id in self._configsvrs]

    @property
    def routers(self):
        """return list of routers"""
        return [{'id': h_id, 'hostname': Hosts().hostname(h_id)} for h_id in self._routers]

    @property
    def members(self):
        """return list of members"""
        # return [{'id': shard, 'hostname': Hosts().hostname(info['_id'])} for shard, info in self._shards.items()]
        return [self.member_info(item) for item in self._shards]

    @property
    def router(self):
        """return first available router"""
        for host in self._routers:
            info = Hosts().info(host)
            logger.debug("router(): info=%r" % info)
            if info['procInfo'].get('alive', False):
                return {'id': host, 'hostname': Hosts().hostname(host)}
        logger.debug("router(): self._routers=%r" % self._routers)

    def router_add(self, params):
        """add new router (mongos) into existing configuration"""
        logger.debug("router_add: %r" % params)
        cfgs = ','.join([Hosts().info(item)['uri'] for item in self._configsvrs])
        params.update({'configdb': cfgs})
        self._routers.append(Hosts().create('mongos', params, sslParams=self.sslParams, autostart=True, auth_key=self.auth_key))
        return {'id': self._routers[-1], 'hostname': Hosts().hostname(self._routers[-1])}

    def connection(self):
        c = MongoClient(self.router['hostname'], **self.kwargs)
        try:
            self.login and self.password and c.admin.authenticate(self.login, self.password)
        except:
            pass
        return c

    def router_command(self, command, arg=None, is_eval=False):
        """run command on the router host

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
        result = Hosts().remove(router_id)
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
            rs_id = RS().create(rs_params)
            members = RS().members(rs_id)
            cfgs = rs_id + r"/" + ','.join([item['host'] for item in members])
            result = self._add(cfgs, member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isReplicaSet': True, '_id': rs_id}
                # return self._shards[result['shardAdded']].copy()
                return self.member_info(member_id)

        else:
            # is single host
            params.update({'autostart': True, 'auth_key': self.auth_key, 'sslParams': self.sslParams})
            params['procParams'] = params.get('procParams', {})
            logger.debug("hosts create params: {params}".format(**locals()))
            host_id = Hosts().create('mongod', **params)
            result = self._add(Hosts().info(host_id)['uri'], member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isHost': True, '_id': host_id}
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
            if shard.get('isHost', False):
                Hosts().remove(shard['_id'])
            if shard.get('isReplicaSet', False):
                RS().remove(shard['_id'])
        return result

    def member_remove(self, member_id):
        """remove member from configuration"""
        return self._remove(member_id)

    def info(self):
        """return info about configuration"""
        return {'id': self.id,
                'members': self.members,
                'configsvrs': self.configsvrs,
                'routers': self.routers,
                'uri': ','.join(x['hostname'] for x in self.routers),
                'orchestration': 'sh'}

    def cleanup(self):
        """cleanup configuration: stop and remove all hosts"""
        for _id, shard in self._shards.items():
            if shard.get('isHost', False):
                Hosts().remove(shard['_id'])
            if shard.get('isReplicaSet', False):
                RS().remove(shard['_id'])

        for mongos in self._routers:
            Hosts().remove(mongos)

        for configsvr in self._configsvrs:
            Hosts().remove(configsvr)

        self._configsvrs = []
        self._routers = []
        self._shards = {}


class Shards(Singleton, Container):
    """ Shards is a dict-like collection for Shard objects"""
    _name = 'shards'
    _obj_type = Shard
    bin_path = ''
    pids_file = tempfile.mktemp(prefix="mongo-")

    def set_settings(self, bin_path=None):
        """set path to storage"""
        super(Shards, self).set_settings(bin_path)
        RS().set_settings(bin_path)

    def __getitem__(self, key):
        return self.info(key)

    def cleanup(self):
        """remove all hosts with their data"""
        for host in self:
            self.remove(host)

    def create(self, params):
        """create new shard
        Args:
           params - dictionary with specific params for instance
        Return shard_id
           where shard_id - id which can use to take the shard from hosts collection
        """
        params['id'] = params.get('id', str(uuid4()))
        shard = Shard(params)
        self[shard.id] = shard
        return shard.id

    def remove(self, shard_id):
        """remove shard and data stuff
        Args:
            shard_id - shard identity
        """
        shard = self._storage.pop(shard_id)
        shard.cleanup()

    def info(self, shard_id):
        """return dictionary object with info about shard
        Args:
            shard_id - shard identity
        """
        return self._storage[shard_id].info()

    def configservers(self, shard_id):
        """return list of config servers"""
        return self._storage[shard_id].configsvrs

    def routers(self, shard_id):
        """return list of routers"""
        return self._storage[shard_id].routers

    def router_add(self, shard_id, params):
        """add new router"""
        shard = self._storage[shard_id]
        result = shard.router_add(params)
        self._storage[shard_id] = shard
        return result

    def router_del(self, shard_id, router_id):
        """remove router from shard cluster"""
        shard = self._storage[shard_id]
        result = shard.router_remove(router_id)
        self._storage[shard_id] = shard
        return result

    def members(self, shard_id):
        """return list of members"""
        return self._storage[shard_id].members

    def member_info(self, shard_id, member_id):
        """return info about member"""
        shard = self._storage[shard_id]
        return shard.member_info(member_id)

    def member_del(self, shard_id, member_id):
        """remove member from shard cluster"""
        shard = self._storage[shard_id]
        result = shard.member_remove(member_id)
        self._storage[shard_id] = shard
        return result

    def member_add(self, shard_id, params):
        """add new member into configuration"""
        shard = self._storage[shard_id]
        result = shard.member_add(params.get('id', None), params.get('shardParams', {}))
        self._storage[shard_id] = shard
        return result
