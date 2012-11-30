#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from uuid import uuid4
from singleton import Singleton
from storage import Storage
import operator
from hosts import Hosts
from rs import RS


class Shards(Singleton):
    """ Shards is a dict-like collection for Shard objects"""
    _storage = None

    def set_settings(self, pids_file, bin_path=None):
        """set path to storage"""
        self._storage = Storage(pids_file, 'shards')
        self.pids_file = pids_file
        self.bin_path = bin_path or ''

    def __getitem__(self, key):
        return self.sh_info(key)

    def __setitem__(self, key, value):
        if isinstance(value, Shard):
            self._storage[key] = value
        else:
            raise ValueError

    def __delitem__(self, key):
        shard = self._storage[key]
        operator.delitem(self._storage, key)
        del(shard)

    def __del__(self):
        self.cleanup()

    def __contains__(self, item):
        return item in self._storage

    def __iter__(self):
        for item in self._storage:
            yield item

    def __len__(self):
        return len(self._storage)

    def cleanup(self):
        """remove all hosts with their data"""
        if self._storage:
            for shard_id in self._storage:
                self.sh_del(shard_id)

    def sh_new(self, params):
        """create new shard
        Args:
           params - dictionary with specific params for instance
        Return shard_id
           where shard_id - id which can use to take the shard from hosts collection
        """
        try:
            params['id'] = params.get('id', str(uuid4()))
            shard = Shard(params)
            self[shard.id] = shard
            return shard.id
        except:
            raise

    def sh_del(self, shard_id):
        """remove shard and data stuff
        Args:
            shard_id - shard identity
        """
        shard = self._storage.pop(shard_id)
        shard.cleanup()

    def sh_info(self, shard_id):
        """return dictionary object with info about shard
        Args:
            shard_id - shard identity
        """
        return self._storage[shard_id].info()

    def sh_configservers(self, shard_id):
        """return list of config servers"""
        return self._storage[shard_id].configsvrs

    def sh_routers(self, shard_id):
        """return list of routers"""
        return self._storage[shard_id].routers

    def sh_router_add(self, shard_id, params):
        """add new router"""
        shard = self._storage[shard_id]
        result = shard.router_add(params)
        self._storage[shard_id] = shard
        return result

    def sh_members(self, shard_id):
        """return list of members"""
        return self._storage[shard_id].members

    def sh_member_info(self, shard_id, member_id):
        """return info about member"""
        shard = self._storage[shard_id]
        return shard.member_info(member_id)

    def sh_member_del(self, shard_id, member_id):
        """remove member from shard cluster"""
        shard = self._storage[shard_id]
        result = shard.member_remove(member_id)
        self._storage[shard_id] = shard
        return result

    def sh_member_add(self, shard_id, params):
        """add new member into configuration"""
        shard = self._storage[shard_id]
        result = shard.member_add(params.get('id', None), params.get('shardParams', {}))
        self._storage[shard_id] = shard
        return result


class Shard(object):
    """class represents Sharding configuration"""

    def __init__(self, params):
        """init configuration acording params"""
        self.id = params.get('id', None) or 'sh-' + str(uuid4())
        self._configsvrs = []
        self._routers = []
        self._shards = {}
        self.__init_configsvr(params.get('configsvrs', [{}]))
        map(self.router_add, params.get('routers', [{}]))
        for cfg in params.get('members', []):
            self.member_add(cfg.get('id', None), cfg.get('shardParams', {}))

    def __init_configsvr(self, params):
        """create and start config servers"""
        self._configsvrs = []
        for cfg in params:
            cfg.update({'configsvr': True})
            self._configsvrs.append(Hosts().h_new('mongod', cfg, autostart=True))

    def __len__(self):
        return len(self._shards)

    @property
    def configsvrs(self):
        """return list of config servers"""
        return [{'id': h_id, 'hostname': Hosts().h_hostname(h_id)} for h_id in self._configsvrs]

    @property
    def routers(self):
        """return list of routers"""
        return [{'id': h_id, 'hostname': Hosts().h_hostname(h_id)} for h_id in self._routers]

    @property
    def members(self):
        """return list of members"""
        # return [{'id': shard, 'hostname': Hosts().h_hostname(info['_id'])} for shard, info in self._shards.items()]
        return [self.member_info(item) for item in self._shards]

    @property
    def router(self):
        """return first available router"""
        for host in self._routers:
            info = Hosts().h_info(host)
            if info['procInfo'].get('alive', False):
                return {'id': host, 'hostname': Hosts().h_hostname(host)}

    def router_add(self, params):
        """add new router (mongos) into existing configuration"""
        cfgs = ','.join([Hosts().h_info(item)['uri'] for item in self._configsvrs])
        params.update({'configdb': cfgs})
        self._routers.append(Hosts().h_new('mongos', params, autostart=True, check_db=False))
        return {'id': self._routers[-1], 'hostname': Hosts().h_hostname(self._routers[-1])}

    def router_command(self, command, arg=None, is_eval=False):
        """run command on router host"""
        return Hosts().h_db_command(self.router['id'], command, arg, is_eval=is_eval)

    def _add(self, shard_uri, name):
        """execute addShard command"""
        return self.router_command("addShard", (shard_uri, {"name": name}), is_eval=False)

    def member_add(self, member_id=None, params=None):
        """add new member into existing configuration"""
        member_id = member_id or str(uuid4())
        if 'members' in params:
            # is replica set
            rs_id = RS().rs_new(params)
            rs_members = RS().rs_members(rs_id)
            cfgs = rs_id + r"/" + ','.join([item['host'] for item in rs_members])
            result = self._add(cfgs, member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isReplicaSet': True, '_id': rs_id}
                # return self._shards[result['shardAdded']].copy()
                return self.member_info(member_id)

        else:
            # is single host
            host_id = Hosts().h_new('mongod', params, autostart=True)
            result = self._add(Hosts().h_info(host_id)['uri'], member_id)
            if result.get('ok', 0) == 1:
                self._shards[result['shardAdded']] = {'isHost': True, '_id': host_id}
                # return self._shards[result['shardAdded']]
                return self.member_info(member_id)

    def member_info(self, member_id):
        """return info about member"""
        info = self._shards[member_id].copy()
        info['id'] = member_id
        return info

    def _remove(self, shard_name):
        """remove member from configuration"""
        result = self.router_command("removeShard", shard_name, is_eval=False)
        if result['ok'] == 1 and result['state'] == 'completed':
            shard = self._shards.pop(shard_name)
            if shard.get('isHost', False):
                Hosts().h_del(shard['_id'])
            if shard.get('isReplicaSet', False):
                RS().rs_del(shard['_id'])
        return result

    def member_remove(self, member_id):
        """remove member from configuration"""
        return self._remove(member_id)

    def info(self):
        """return info about configuration"""
        return {'id': self.id,
                'members': self.members,
                'configsvrs': self.configsvrs,
                'routers': self.routers}

    def cleanup(self):
        """cleanup configuration: stop and remove all hosts"""
        for _id, shard in self._shards.items():
            if shard.get('isHost', False):
                Hosts().h_del(shard['_id'])
            if shard.get('isReplicaSet', False):
                RS().rs_del(shard['_id'])

        for mongos in self._routers:
            Hosts().h_del(mongos)

        for configsvr in self._configsvrs:
            Hosts().h_del(configsvr)

        self._configsvrs = []
        self._routers = []
        self._shards = {}
