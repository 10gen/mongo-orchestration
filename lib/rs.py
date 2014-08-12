#!/usr/bin/python
# coding=utf-8

import logging
logger = logging.getLogger(__name__)
from uuid import uuid4
from lib.singleton import Singleton
from lib.container import Container
import pymongo
from lib.hosts import Hosts
import time
import lib.errors
import tempfile
import sys
import traceback

Hosts()


class ReplicaSet(object):
    """class represents ReplicaSet"""

    _hosts = Hosts()  # singleton to manage hosts instances
    # replica set's default parameters
    default_params = {'arbiterOnly': False, 'buildIndexes': False, 'hidden': False, 'slaveDelay': 0}

    def __init__(self, rs_params):
        """create replica set according members config
        Args:
            rs_params - replica set configuration
        """
        self.host_map = {}
        self.auth_key = rs_params.get('auth_key', None)
        self.login = rs_params.get('login', '')
        self.password = rs_params.get('password', '')
        self.repl_id = rs_params.get('id', None) or "rs-" + str(uuid4())

        self.sslParams = rs_params.get('sslParams', {})
        self.kwargs = {}

        if not not self.sslParams:
            self.kwargs['ssl'] = True

        config = {"_id": self.repl_id, "members": [
                  self.member_create(member, index) for index, member in enumerate(rs_params.get('members', {}))
                  ]}
        logger.debug("replica config: {config}".format(**locals()))
        if not self.repl_init(config):
            self.cleanup()
            raise lib.errors.ReplicaSetError("replica can't started")

        if self.login:
            logger.debug("add admin user {login}/{password}".format(login=self.login, password=self.password))
            try:
                c = self.connection()
                c.admin.add_user(self.login, self.password,
                                 roles=['__system',
                                        'clusterAdmin',
                                        'dbAdminAnyDatabase',
                                        'readWriteAnyDatabase',
                                        'userAdminAnyDatabase'])
            except pymongo.errors.OperationFailure:
                pass
            finally:
                c.close()

    def __len__(self):
        return len(self.host_map)

    def cleanup(self):
        """remove all members without reconfig"""
        for item in self.host_map:
            self.member_del(item, reconfig=False)
        self.host_map.clear()

    def id2host(self, member_id):
        """return hostname by member id"""
        return self.host_map[member_id]

    def host2id(self, hostname):
        """return member id by hostname"""
        for key, value in self.host_map.items():
            if value == hostname:
                return key

    def update_host_map(self, config):
        """update host_map ({member_id:hostname})"""
        self.host_map = dict([(member['_id'], member['host']) for member in config['members']])

    def repl_init(self, config):
        """create replica set by config
        return True if replica set created successfuly, else False"""
        self.update_host_map(config)
        # init_host - host which can init replica set
        init_host = [member['host'] for member in config['members']
                     if not (member.get('arbiterOnly', False)
                             or member.get('priority', 1) == 0)][0]

        hosts = [member['host'] for member in config['members']]
        if not self.wait_while_reachable(hosts):
            logger.error("all hosts must be reachable")
            self.cleanup()
            return False

        try:
            result = self.connection(init_host).admin.command("replSetInitiate", config)
            logger.debug("replica init result: {result}".format(**locals()))
        except pymongo.errors.PyMongoError:
            raise
        if int(result.get('ok', 0)) == 1:
            # wait while real state equals config
            return self.waiting_config_state()
        else:
            self.cleanup()
            return False

    def repl_update(self, config):
        """Reconfig Replicaset with new config"""
        cfg = config.copy()
        cfg['version'] += 1
        try:
            result = self.run_command("replSetReconfig", cfg)
            if int(result.get('ok', 0)) != 1:
                return False
        except pymongo.errors.AutoReconnect:
            self.update_host_map(cfg)  # use new host_map
        self.waiting_config_state()
        return self.connection() and True

    def info(self):
        """return information about replica set"""
        return {"id": self.repl_id,
                "auth_key": self.auth_key,
                "members": self.members(),
                "uri": ','.join(x['host'] for x in self.members()) + '/?replicaSet=' + self.repl_id,
                "orchestration": 'rs'}

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
            raise lib.errors.MongoOrchestrationError()
        return member_id

    def run_command(self, command, arg=None, is_eval=False, member_id=None):
        """run command on replica set
        if member_id is specified command will be execute on this host
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
            hostname = self.id2host(member_id)
        result = getattr(self.connection(hostname=hostname).admin, mode)(command, arg)
        logger.debug("command result: {result}".format(result=result))
        return result

    @property
    def config(self):
        """return replica set config, use rs.conf() command"""
        config = self.run_command("rs.conf()", is_eval=True)
        return config

    def member_create(self, params, member_id):
        """start new mongod instances as part of replica set
        Args:
            params - member params
            member_id - member index

        return member config
        """
        member_config = params.get('rsParams', {})
        proc_params = {'replSet': self.repl_id}
        proc_params.update(params.get('procParams', {}))

        host_id = self._hosts.create('mongod', proc_params, self.sslParams, self.auth_key)
        member_config.update({"_id": member_id, "host": self._hosts.info(host_id)['uri']})
        return member_config

    def member_del(self, member_id, reconfig=True):
        """remove member from replica set
        Args:
            member_id - member index
            reconfig - is need reconfig replica

        return True if operation success otherwise False
        """
        host_id = self._hosts.id_by_hostname(self.id2host(member_id))
        if reconfig and member_id in [member['_id'] for member in self.members()]:
            config = self.config
            config['members'].pop(member_id)
            self.repl_update(config)
        self._hosts.remove(host_id)
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
        host_id = self._hosts.id_by_hostname(self.id2host(member_id))
        host_info = self._hosts.info(host_id)
        result = {'_id': member_id, 'uri': host_info['uri'], 'host_id': host_id, 'procInfo': host_info['procInfo'], 'statuses': host_info['statuses']}
        result['rsInfo'] = {}
        if host_info['procInfo']['alive']:
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
        host_id = self._hosts.id_by_hostname(self.id2host(member_id))
        return self._hosts.command(host_id, command)

    def member_freeze(self, member_id, timeout):
        """apply command (start/stop/restart) to member instance of replica set
        Args:
            member_id - member index
            timeout - duration of this operation

        return True if operation success otherwise False
        """
        # return self.run_command("rs.freeze({timeout})".format(timeout=timeout), is_eval=True, member_id=member_id)
        # result = c.admin.command("replSetFreeze", 10)
        return self.run_command("replSetFreeze", timeout, is_eval=False, member_id=member_id)

    def members(self):
        """return list of members information"""
        result = list()
        for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']:
            result.append({"_id": member['_id'], "host": member["name"], "host_id": self._hosts.id_by_hostname(member["name"])})
        return result

    def stepdown(self, timeout=60):
        """stepdown primary host
        Args:
            timeout - number of seconds to avoid election to primary.

        return True if operation success otherwise False
        """
        try:
            self.run_command("replSetStepDown", timeout, is_eval=False)
        except (pymongo.errors.AutoReconnect):
            pass
        time.sleep(2)
        return self.connection() and True

    def primary(self):
        """return primary hostname of replica set"""
        host, port = self.connection().primary
        return "{host}:{port}".format(**locals())

    def get_members_in_state(self, state):
        """return all members of replica set in specific state"""
        members = self.run_command(command='replSetGetStatus', is_eval=False)['members']
        return [member['name'] for member in members if member['state'] == state]

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
        # hosts = member_id is not None and self.id2host(member_id) or ",".join(self.host_map.values())
        hosts = hostname or ",".join(self.host_map.values())
        while True:
            try:
                if hostname is None:
                    c = pymongo.MongoReplicaSetClient(hosts, replicaSet=self.repl_id, read_preference=read_preference, socketTimeoutMS=20000, **self.kwargs)
                    if c.primary:
                        try:
                            self.login and self.password and c.admin.authenticate(self.login, self.password)
                        except:
                            pass
                        return c
                    raise pymongo.errors.AutoReconnect("No replica set primary available")
                else:
                    logger.debug("connection to the {hosts}".format(**locals()))
                    c = pymongo.MongoClient(hosts, socketTimeoutMS=20000, **self.kwargs)
                    if self.login and self.password:
                        try:
                            c.admin.authenticate(self.login, self.password)
                        except:
                            pass
                    return c
            except (pymongo.errors.PyMongoError):
                exc_type, exc_value, exc_tb = sys.exc_info()
                err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
                logger.error("Exception {exc_type} {exc_value}".format(**locals()))
                logger.error(err_message)
                if time.time() - t_start > timeout:
                    raise pymongo.errors.AutoReconnect("Couldn't connect while timeout {timeout} second".format(**locals()))
                time.sleep(10)

    def secondaries(self):
        """return list of secondaries members"""
        return [{"_id": self.host2id(member), "host": member, "host_id": self._hosts.id_by_hostname(member)} for member in self.get_members_in_state(2)]

    def arbiters(self):
        """return list of arbiters"""
        return [{"_id": self.host2id(member), "host": member, "host_id": self._hosts.id_by_hostname(member)} for member in self.get_members_in_state(7)]

    def hidden(self):
        """return list of hidden members"""
        members = [self.member_info(item["_id"]) for item in self.members()]
        return [{"_id": member['_id'], "host": member['uri'], "host_id": self._hosts.id_by_hostname(member['uri'])} for member in members if member['rsInfo'].get('hidden', False)]

    def passives(self):
        """return list of passive hosts"""
        hosts = self.run_command('ismaster').get('passives', [])
        return [member for member in self.members() if member['host'] in hosts]

    def hosts(self):
        """return list of hosts (not hidden nodes)"""
        hosts = self.run_command('ismaster').get('hosts', [])
        return [member for member in self.members() if member['host'] in hosts]

    def wait_while_reachable(self, hosts, timeout=60):
        """wait while all hosts be reachable
        Args:
            hosts - list of hosts
        """
        t_start = time.time()
        while True:
            try:
                for host in hosts:
                    # TODO: use state code to check if host is reachable
                    server_info = self.connection(hostname=host, timeout=5).server_info()
                    logger.debug("server_info: {server_info}".format(server_info=server_info))
                    if int(server_info['ok']) != 1:
                        raise pymongo.errors.OperationFailure("{host} is not reachable".format(**locals))
                # logger.debug("rs status: {rs_status}".format(rs_status=self.run_command("rs.status()", is_eval=True)['members']))
                return True
            except (KeyError, AttributeError, pymongo.errors.AutoReconnect, pymongo.errors.OperationFailure):
                if time.time() - t_start > timeout:
                    return False
                time.sleep(2)

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
            time.sleep(8)
        return True

    def check_config_state(self):
        "return True if real state equal config state otherwise False"
        try:
            if len(filter(lambda item: item['state'] in (3, 4, 5, 6, 9), self.run_command("rs.status()", is_eval=True)['members'])) > 0:
                return False
        except pymongo.errors.AutoReconnect:
            # catch 'No replica set primary available' Exception
            return False
        logger.debug("all members in correct state")
        config = self.config
        self.update_host_map(config)
        for member in config['members']:
            cfg_member_info = self.default_params.copy()
            cfg_member_info.update(member)
            'priority' in cfg_member_info and cfg_member_info.pop('priority')  # no way to check 'priority' value
            'votes' in cfg_member_info and cfg_member_info.pop('votes')  # no way to check 'votes' value
            'tags' in cfg_member_info and cfg_member_info.pop('tags')  # no way to check 'tags' value
            cfg_member_info['host'] = cfg_member_info['host'].lower()

            real_member_info = self.default_params.copy()
            info = self.member_info(member["_id"])
            real_member_info["_id"] = info['_id']
            real_member_info["host"] = info["uri"].lower()
            real_member_info.update(info['rsInfo'])
            logger.debug("real_member_info({member_id}): {info}".format(member_id=member['_id'], info=info))
            for key in cfg_member_info:
                if cfg_member_info[key] != real_member_info.get(key, None):
                    logger.debug("{key}: {value1} ! = {value2}".format(key=key, value1=cfg_member_info[key], value2=real_member_info.get(key, None)))
                    return False
        return True


class RS(Singleton, Container):
    """ RS is a dict-like collection for replica set"""
    _name = 'rs'
    _obj_type = ReplicaSet
    bin_path = ''
    pids_file = tempfile.mktemp(prefix="mongo-")

    def set_settings(self, bin_path=''):
        """set path to storage"""
        super(RS, self).set_settings(bin_path)
        Hosts().set_settings(bin_path)

    def cleanup(self):
        """remove all hosts with their data"""
        Hosts().cleanup()
        self._storage and self._storage.clear()

    def create(self, rs_params):
        """create new replica set
        Args:
           rs_params - replica set configuration
        Return repl_id which can use to take the replica set
        """
        repl_id = rs_params.get('id', None)
        if repl_id is not None and repl_id in self:
            raise lib.errors.ReplicaSetError("replica set with id={id} already exists".format(id=repl_id))
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

    def primary_stepdown(self, repl_id, timeout=60):
        """stepdown primary node
        Args:
            repld_id - replica set identity
            timeout - number of seconds to avoid election to primary
        return True if operation success otherwise False
        """
        repl = self[repl_id]
        return repl.stepdown(timeout)

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

    def hosts(self, repl_id):
        """return list of hosts"""
        return self[repl_id].hosts()

    def member_info(self, repl_id, member_id):
        """return information about member
        Args:
            repl_id - replica set identity
            member_id - member index
        """
        return self[repl_id].member_info(member_id)

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

    def member_freeze(self, repl_id, member_id, timeout):
        """apply command 'freeze' to the member of replica set
        Args:
            repl_id - replica set identity
            member_id - member index
            timeout - duration of this operation

        return True if operation success otherwise False
        """
        repl = self[repl_id]
        result = repl.member_freeze(member_id, timeout)
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
