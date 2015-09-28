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
import tempfile
import time
import traceback

from uuid import uuid4

import pymongo

from mongo_orchestration.common import (
    BaseModel, connected, DEFAULT_SUBJECT, DEFAULT_SSL_OPTIONS)
from mongo_orchestration.singleton import Singleton
from mongo_orchestration.container import Container
from mongo_orchestration.errors import ReplicaSetError
from mongo_orchestration.servers import Servers

logger = logging.getLogger(__name__)
Servers()


class ReplicaSet(BaseModel):
    """class represents ReplicaSet"""

    _servers = Servers()  # singleton to manage servers instances
    # replica set's default parameters
    default_params = {'arbiterOnly': False, 'hidden': False, 'slaveDelay': 0}

    def __init__(self, rs_params):
        """create replica set according members config
        Args:
            rs_params - replica set configuration
        """
        self.server_map = {}
        self.auth_key = rs_params.get('auth_key', None)
        self.login = rs_params.get('login', '')
        self.auth_source = rs_params.get('authSource', 'admin')
        self.password = rs_params.get('password', '')
        self.admin_added = False
        self.repl_id = rs_params.get('id', None) or str(uuid4())
        self._version = rs_params.get('version')

        self.sslParams = rs_params.get('sslParams', {})
        self.kwargs = {}
        self.restart_required = self.login or self.auth_key
        self.x509_extra_user = False

        if self.sslParams:
            self.kwargs.update(DEFAULT_SSL_OPTIONS)

        members = rs_params.get('members', {})
        config = {"_id": self.repl_id, "members": [
            self.member_create(member, index)
            for index, member in enumerate(members)
        ]}
        if 'rsSettings' in rs_params:
            config['settings'] = rs_params['rsSettings']
        # Explicitly set write concern to number of data-bearing members.
        # If we add a user later, we need to guarantee that every node
        # has the user before we authenticate ('majority' is insufficient).
        self._write_concern = len(
            [m for m in members
             if not m.get('rsParams', {}).get('arbiterOnly')]
        )

        logger.debug("replica config: {config}".format(**locals()))
        if not self.repl_init(config):
            self.cleanup()
            raise ReplicaSetError("Could not create replica set.")

        if not self.waiting_config_state():
            raise ReplicaSetError(
                "Could not actualize replica set configuration.")

        if self.login:
            # If the only authentication mechanism enabled is MONGODB-X509,
            # we'll need to add our own user using SSL certificates we already
            # have. Otherwise, the user of MO would have to copy their own
            # certificates to wherever MO happens to be running so that MO
            # might authenticate.
            for member in members:
                proc_params = member.get('procParams', {})
                set_params = proc_params.get('setParameter', {})
                auth_mechs = set_params.get('authenticationMechanisms', '')
                auth_mechs = auth_mechs.split(',')
                if len(auth_mechs) == 1 and auth_mechs[0] == 'MONGODB-X509':
                    self.x509_extra_user = True
                    break

            self._add_users(self.connection()[self.auth_source])
        if self.restart_required:
            # Restart all the servers with auth flags and ssl.
            for idx, member in enumerate(members):
                server_id = self._servers.host_to_server_id(
                    self.member_id_to_host(idx))
                server = self._servers._storage[server_id]
                # If this is an arbiter, we can't authenticate as the user,
                # so don't set the login/password.
                if not member.get('rsParams', {}).get('arbiterOnly'):
                    server.x509_extra_user = self.x509_extra_user
                    server.auth_source = self.auth_source
                    server.login = self.login
                    server.password = self.password

                def add_auth(config):
                    if self.auth_key:
                        config['keyFile'] = self.key_file
                    config.update(member.get('procParams', {}))
                    return config

                server.restart(config_callback=add_auth)
            self.restart_required = False

        if not self.waiting_member_state() and self.waiting_config_state():
            raise ReplicaSetError(
                "Could not actualize replica set configuration.")
        for i in range(100):
            if self.connection().primary:
                break
            time.sleep(0.1)
        else:
            raise ReplicaSetError("No primary was ever elected.")

    def __len__(self):
        return len(self.server_map)

    def cleanup(self):
        """remove all members without reconfig"""
        for item in self.server_map:
            self.member_del(item, reconfig=False)
        self.server_map.clear()

    def member_id_to_host(self, member_id):
        """return hostname by member id"""
        return self.server_map[member_id]

    def host2id(self, hostname):
        """return member id by hostname"""
        for key, value in self.server_map.items():
            if value == hostname:
                return key

    def update_server_map(self, config):
        """update server_map ({member_id:hostname})"""
        self.server_map = dict([(member['_id'], member['host']) for member in config['members']])

    def repl_init(self, config):
        """create replica set by config
        return True if replica set created successfuly, else False"""
        self.update_server_map(config)
        # init_server - server which can init replica set
        init_server = [member['host'] for member in config['members']
                       if not (member.get('arbiterOnly', False)
                               or member.get('priority', 1) == 0)][0]

        servers = [member['host'] for member in config['members']]
        if not self.wait_while_reachable(servers):
            logger.error("all servers must be reachable")
            self.cleanup()
            return False
        try:
            result = self.connection(init_server).admin.command("replSetInitiate", config)
            logger.debug("replica init result: {result}".format(**locals()))
        except pymongo.errors.PyMongoError:
            raise
        if int(result.get('ok', 0)) == 1:
            # Wait while members come up
            return self.waiting_member_state()
        else:
            self.cleanup()
            return False

    def reset(self):
        """Ensure all members are running and available."""
        # Need to use self.server_map, in case no Servers are left running.
        for member_id in self.server_map:
            host = self.member_id_to_host(member_id)
            server_id = self._servers.host_to_server_id(host)
            # Reset each member.
            self._servers.command(server_id, 'reset')
        # Wait for all members to have a state of 1, 2, or 7.
        # Note that this also waits for a primary to become available.
        self.waiting_member_state()
        # Wait for Server states to match the config from the primary.
        self.waiting_config_state()
        return self.info()

    def repl_update(self, config):
        """Reconfig Replicaset with new config"""
        cfg = config.copy()
        cfg['version'] += 1
        try:
            result = self.run_command("replSetReconfig", cfg)
            if int(result.get('ok', 0)) != 1:
                return False
        except pymongo.errors.AutoReconnect:
            self.update_server_map(cfg)  # use new server_map
        self.waiting_member_state()
        self.waiting_config_state()
        return self.connection() and True

    def info(self):
        """return information about replica set"""
        hosts = ','.join(x['host'] for x in self.members())
        mongodb_uri = 'mongodb://' + hosts + '/?replicaSet=' + self.repl_id
        result = {"id": self.repl_id,
                  "auth_key": self.auth_key,
                  "members": self.members(),
                  "mongodb_uri": mongodb_uri,
                  "orchestration": 'replica_sets'}
        if self.login:
            # Add replicaSet URI parameter.
            uri = ('%s&replicaSet=%s'
                   % (self.mongodb_auth_uri(hosts), self.repl_id))
            result['mongodb_auth_uri'] = uri
        return result

    def repl_member_add(self, params):
        """create new mongod instances and add it to the replica set.
        Args:
            params - mongod params
        return True if operation success otherwise False
        """
        repl_config = self.config
        member_id = max([member['_id'] for member in repl_config['members']]) + 1
        member_config = self.member_create(params, member_id)
        repl_config['members'].append(member_config)
        if not self.repl_update(repl_config):
            self.member_del(member_id, reconfig=True)
            raise ReplicaSetError("Could not add member to ReplicaSet.")
        return member_id

    def run_command(self, command, arg=None, is_eval=False, member_id=None):
        """run command on replica set
        if member_id is specified command will be execute on this server
        if member_id is not specified command will be execute on the primary

        Args:
            command - command string
            arg - command argument
            is_eval - if True execute command as eval
            member_id - member id

        return command's result
        """
        logger.debug("run_command({command}, {arg}, {is_eval}, {member_id})".format(**locals()))
        mode = is_eval and 'eval' or 'command'
        hostname = None
        if isinstance(member_id, int):
            hostname = self.member_id_to_host(member_id)
        result = getattr(self.connection(hostname=hostname).admin, mode)(command, arg)
        logger.debug("command result: {result}".format(result=result))
        return result

    @property
    def config(self):
        """return replica set config, use rs.conf() command"""
        try:
            admin = self.connection().admin
            config = admin.command('replSetGetConfig')['config']
        except pymongo.errors.OperationFailure:
            # replSetGetConfig was introduced in 2.7.5.
            config = self.connection().local.system.replset.find_one()
        return config

    def member_create(self, params, member_id):
        """start new mongod instances as part of replica set
        Args:
            params - member params
            member_id - member index

        return member config
        """
        member_config = params.get('rsParams', {})
        server_id = params.pop('server_id', None)
        version = params.pop('version', self._version)
        proc_params = {'replSet': self.repl_id}
        proc_params.update(params.get('procParams', {}))
        # Make sure that auth isn't set the first time we start the servers.
        proc_params = self._strip_auth(proc_params)

        # Don't pass in auth_key the first time we start the servers.
        server_id = self._servers.create(
            name='mongod',
            procParams=proc_params,
            sslParams=self.sslParams,
            version=version,
            server_id=server_id
        )
        member_config.update({"_id": member_id,
                              "host": self._servers.hostname(server_id)})
        return member_config

    def member_del(self, member_id, reconfig=True):
        """remove member from replica set
        Args:
            member_id - member index
            reconfig - is need reconfig replica

        return True if operation success otherwise False
        """
        server_id = self._servers.host_to_server_id(
            self.member_id_to_host(member_id))
        if reconfig and member_id in [member['_id'] for member in self.members()]:
            config = self.config
            config['members'].pop(member_id)
            self.repl_update(config)
        self._servers.remove(server_id)
        return True

    def member_update(self, member_id, params):
        """update member's values with reconfig replica
        Args:
            member_id - member index
            params - updates member params

        return True if operation success otherwise False
        """
        config = self.config
        config['members'][member_id].update(params.get("rsParams", {}))
        return self.repl_update(config)

    def member_info(self, member_id):
        """return information about member"""
        server_id = self._servers.host_to_server_id(
            self.member_id_to_host(member_id))
        server_info = self._servers.info(server_id)
        result = {'_id': member_id, 'server_id': server_id,
                  'mongodb_uri': server_info['mongodb_uri'],
                  'procInfo': server_info['procInfo'],
                  'statuses': server_info['statuses']}
        if self.login:
            result['mongodb_auth_uri'] = self.mongodb_auth_uri(
                self._servers.hostname(server_id))
        result['rsInfo'] = {}
        if server_info['procInfo']['alive']:
            # Can't call serverStatus on arbiter when running with auth enabled.
            # (SERVER-5479)
            if self.login or self.auth_key:
                arbiter_ids = map(lambda member: member['_id'], self.arbiters())
                if member_id in arbiter_ids:
                    result['rsInfo'] = {
                        'arbiterOnly': True, 'secondary': False, 'primary': False}
                    return result
            repl = self.run_command('serverStatus', arg=None, is_eval=False, member_id=member_id)['repl']
            logger.debug("member {member_id} repl info: {repl}".format(**locals()))
            for key in ('votes', 'tags', 'arbiterOnly', 'buildIndexes', 'hidden', 'priority', 'slaveDelay', 'votes', 'secondary'):
                if key in repl:
                    result['rsInfo'][key] = repl[key]
            result['rsInfo']['primary'] = repl.get('ismaster', False)

        return result

    def member_command(self, member_id, command):
        """apply command (start/stop/restart) to member instance of replica set
        Args:
            member_id - member index
            command - string command (start/stop/restart)

        return True if operation success otherwise False
        """
        server_id = self._servers.host_to_server_id(
            self.member_id_to_host(member_id))
        return self._servers.command(server_id, command)

    def members(self):
        """return list of members information"""
        result = list()
        for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']:
            result.append({
                "_id": member['_id'],
                "host": member["name"],
                "server_id": self._servers.host_to_server_id(member["name"]),
                "state": member['state']
            })
        return result

    def primary(self):
        """return primary hostname of replica set"""
        host, port = self.connection().primary
        return "{host}:{port}".format(**locals())

    def get_members_in_state(self, state):
        """return all members of replica set in specific state"""
        members = self.run_command(command='replSetGetStatus', is_eval=False)['members']
        return [member['name'] for member in members if member['state'] == state]

    def _authenticate_client(self, client):
        """Authenticate the client if necessary."""
        if self.login and not self.restart_required:
            try:
                db = client[self.auth_source]
                if self.x509_extra_user:
                    db.authenticate(
                        DEFAULT_SUBJECT,
                        mechanism='MONGODB-X509'
                    )
                else:
                    db.authenticate(
                        self.login, self.password)
            except:
                logger.exception(
                    "Could not authenticate to %s:%d as %s/%s"
                    % (client.host, client.port, self.login, self.password))
                raise

    def connection(self, hostname=None, read_preference=pymongo.ReadPreference.PRIMARY, timeout=300):
        """return MongoReplicaSetClient object if hostname specified
        return MongoClient object if hostname doesn't specified
        Args:
            hostname - connection uri
            read_preference - default PRIMARY
            timeout - specify how long, in seconds, a command can take before server times out.
        """
        logger.debug("connection({hostname}, {read_preference}, {timeout})".format(**locals()))
        t_start = time.time()
        servers = hostname or ",".join(self.server_map.values())
        while True:
            try:
                if hostname is None:
                    c = pymongo.MongoReplicaSetClient(
                        servers, replicaSet=self.repl_id,
                        read_preference=read_preference,
                        socketTimeoutMS=self.socket_timeout,
                        w=self._write_concern, fsync=True, **self.kwargs)
                    connected(c)
                    if c.primary:
                        self._authenticate_client(c)
                        return c
                    raise pymongo.errors.AutoReconnect("No replica set primary available")
                else:
                    logger.debug("connection to the {servers}".format(**locals()))
                    c = pymongo.MongoClient(
                        servers, socketTimeoutMS=self.socket_timeout,
                        w=self._write_concern, fsync=True, **self.kwargs)
                    connected(c)
                    self._authenticate_client(c)
                    return c
            except (pymongo.errors.PyMongoError):
                exc_type, exc_value, exc_tb = sys.exc_info()
                err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
                logger.error("Exception {exc_type} {exc_value}".format(**locals()))
                logger.error(err_message)
                if time.time() - t_start > timeout:
                    raise pymongo.errors.AutoReconnect("Couldn't connect while timeout {timeout} second".format(**locals()))
                time.sleep(1)

    def secondaries(self):
        """return list of secondaries members"""
        return [
            {
                "_id": self.host2id(member),
                "host": member,
                "server_id": self._servers.host_to_server_id(member)
            }
            for member in self.get_members_in_state(2)
        ]

    def arbiters(self):
        """return list of arbiters"""
        return [
            {
                "_id": self.host2id(member),
                "host": member,
                "server_id": self._servers.host_to_server_id(member)
            }
            for member in self.get_members_in_state(7)
        ]

    def hidden(self):
        """return list of hidden members"""
        members = [self.member_info(item["_id"]) for item in self.members()]
        result = []
        for member in members:
            if member['rsInfo'].get('hidden'):
                server_id = member['server_id']
                result.append({
                    '_id': member['_id'],
                    'host': self._servers.hostname(server_id),
                    'server_id': server_id})
        return result

    def passives(self):
        """return list of passive servers"""
        servers = self.run_command('ismaster').get('passives', [])
        return [member for member in self.members() if member['host'] in servers]

    def servers(self):
        """return list of servers (not hidden nodes)"""
        servers = self.run_command('ismaster').get('hosts', [])
        return [member for member in self.members() if member['host'] in servers]

    def wait_while_reachable(self, servers, timeout=60):
        """wait while all servers be reachable
        Args:
            servers - list of servers
        """
        t_start = time.time()
        while True:
            try:
                for server in servers:
                    # TODO: use state code to check if server is reachable
                    server_info = self.connection(
                        hostname=server, timeout=5).admin.command('ismaster')
                    logger.debug("server_info: {server_info}".format(server_info=server_info))
                    if int(server_info['ok']) != 1:
                        raise pymongo.errors.OperationFailure("{server} is not reachable".format(**locals))
                return True
            except (KeyError, AttributeError, pymongo.errors.AutoReconnect, pymongo.errors.OperationFailure):
                if time.time() - t_start > timeout:
                    return False
                time.sleep(0.1)

    def waiting_member_state(self, timeout=300):
        """Wait for all RS members to be in an acceptable state."""
        t_start = time.time()
        while not self.check_member_state():
            if time.time() - t_start > timeout:
                return False
            time.sleep(0.1)
        return True

    def waiting_config_state(self, timeout=300):
        """waiting while real state equal config state
        Args:
            timeout - specify how long, in seconds, a command can take before server times out.

        return True if operation success otherwise False
        """
        t_start = time.time()
        while not self.check_config_state():
            if time.time() - t_start > timeout:
                return False
            time.sleep(0.1)
        return True

    def check_member_state(self):
        """Verify that all RS members have an acceptable state."""
        bad_states = (3, 4, 5, 6, 9)
        try:
            rs_status = self.run_command('replSetGetStatus')
            bad_members = [member for member in rs_status['members']
                           if member['state'] in bad_states]
            if bad_members:
                return False
        except pymongo.errors.AutoReconnect:
            # catch 'No replica set primary available' Exception
            return False
        logger.debug("all members in correct state")
        return True

    def check_config_state(self):
        """Return True if real state equal config state otherwise False."""
        config = self.config
        self.update_server_map(config)
        for member in config['members']:
            cfg_member_info = self.default_params.copy()
            cfg_member_info.update(member)
            # Remove attributes we can't check.
            for attr in ('priority', 'votes', 'tags', 'buildIndexes'):
                cfg_member_info.pop(attr, None)
            cfg_member_info['host'] = cfg_member_info['host'].lower()

            real_member_info = self.default_params.copy()
            info = self.member_info(member["_id"])
            real_member_info["_id"] = info['_id']
            member_hostname = self._servers.hostname(info['server_id'])
            real_member_info["host"] = member_hostname.lower()
            real_member_info.update(info['rsInfo'])
            logger.debug("real_member_info({member_id}): {info}".format(member_id=member['_id'], info=info))
            for key in cfg_member_info:
                if cfg_member_info[key] != real_member_info.get(key, None):
                    logger.debug("{key}: {value1} ! = {value2}".format(key=key, value1=cfg_member_info[key], value2=real_member_info.get(key, None)))
                    return False
        return True

    def restart(self, timeout=300, config_callback=None):
        """Restart each member of the replica set."""
        for member_id in self.server_map:
            host = self.server_map[member_id]
            server_id = self._servers.host_to_server_id(host)
            server = self._servers._storage[server_id]
            server.restart(timeout, config_callback)


class ReplicaSets(Singleton, Container):
    """ ReplicaSets is a dict-like collection for replica set"""
    _name = 'rs'
    _obj_type = ReplicaSet
    releases = {}
    pids_file = tempfile.mktemp(prefix="mongo-")

    def set_settings(self, releases=None, default_release=None):
        """set path to storage"""
        super(ReplicaSets, self).set_settings(releases, default_release)
        Servers().set_settings(releases, default_release)

    def cleanup(self):
        """remove all servers with their data"""
        Servers().cleanup()
        self._storage and self._storage.clear()

    def create(self, rs_params):
        """create new replica set
        Args:
           rs_params - replica set configuration
        Return repl_id which can use to take the replica set
        """
        repl_id = rs_params.get('id', None)
        if repl_id is not None and repl_id in self:
            raise ReplicaSetError(
                "replica set with id={id} already exists".format(id=repl_id))
        repl = ReplicaSet(rs_params)
        self[repl.repl_id] = repl
        return repl.repl_id

    def info(self, repl_id):
        """return information about replica set
        Args:
            repl_id - replica set identity
        """
        return self[repl_id].info()

    def primary(self, repl_id):
        """find and return primary hostname
        Args:
            repl_id - replica set identity
        """
        repl = self[repl_id]
        primary = repl.primary()
        return repl.member_info(repl.host2id(primary))

    def remove(self, repl_id):
        """remove replica set with kill members
        Args:
            repl_id - replica set identity
        return True if operation success otherwise False
        """
        repl = self._storage.pop(repl_id)
        repl.cleanup()
        del(repl)

    def members(self, repl_id):
        """return list [{"_id": member_id, "host": hostname}] of replica set members
        Args:
            repl_id - replica set identity
        """
        return self[repl_id].members()

    def secondaries(self, repl_id):
        """return list of secondaries members"""
        return self[repl_id].secondaries()

    def arbiters(self, repl_id):
        """return list of arbiters"""
        return self[repl_id].arbiters()

    def hidden(self, repl_id):
        """return list of hidden members"""
        return self[repl_id].hidden()

    def passives(self, repl_id):
        """return list of passive nodes"""
        return self[repl_id].passives()

    def servers(self, repl_id):
        """return list of servers"""
        return self[repl_id].servers()

    def member_info(self, repl_id, member_id):
        """return information about member
        Args:
            repl_id - replica set identity
            member_id - member index
        """
        return self[repl_id].member_info(member_id)

    def command(self, rs_id, command, *args):
        """Call a ReplicaSet method."""
        rs = self._storage[rs_id]
        try:
            return getattr(rs, command)(*args)
        except AttributeError:
            raise ValueError("Cannot issue the command %r to ReplicaSet %s"
                             % (command, rs_id))

    def member_del(self, repl_id, member_id):
        """remove member from replica set (reconfig replica)
        Args:
            repl_id - replica set identity
            member_id - member index
        """
        repl = self[repl_id]
        result = repl.member_del(member_id)
        self[repl_id] = repl
        return result

    def member_add(self, repl_id, params):
        """create instance and add it to existing replcia
        Args:
            repl_id - replica set identity
            params - member params

        return True if operation success otherwise False
        """
        repl = self[repl_id]
        member_id = repl.repl_member_add(params)
        self[repl_id] = repl
        return member_id

    def member_command(self, repl_id, member_id, command):
        """apply command(start, stop, restart) to the member of replica set
        Args:
            repl_id - replica set identity
            member_id - member index
            command - command: start, stop, restart

        return True if operation success otherwise False
        """
        repl = self[repl_id]
        result = repl.member_command(member_id, command)
        self[repl_id] = repl
        return result

    def member_update(self, repl_id, member_id, params):
        """apply new params to replica set member
        Args:
            repl_id - replica set identity
            member_id - member index
            params - new member's params

        return True if operation success otherwise False
        """
        repl = self[repl_id]
        result = repl.member_update(member_id, params)
        self[repl_id] = repl
        return result
