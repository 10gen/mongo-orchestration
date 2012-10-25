# coding=utf-8
import logging
logger = logging.getLogger(__name__)
from uuid import uuid4
from singleton import Singleton
from storage import Storage
import pymongo
from hosts import Hosts
import time


class RS(Singleton):
    """ RS is a dict-like collection for replica set"""
    _storage = None

    def set_settings(self, pids_file):
        """set path to storage"""
        self._storage = Storage(pids_file, 'rs')
        self.pids_file = pids_file
        Hosts().set_settings(pids_file)
        self.cleanup()

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        if isinstance(value, ReplicaSet):
            self._storage[key] = value
        else:
            raise ValueError

    def __delitem__(self, key):
        rs = self._storage.popitem(key)
        del(rs)

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
        logger.info("cleanup replica set collection")
        """remove all hosts with their data"""
        self._storage.clear()

    def rs_new(self, members, auth_key=None, timeout=300):
        """create new replica set
        Args:
           members - list of members params
           auth_key - authorization key
           timeout -  specify how long, in seconds, a command can take before times out.
        Return repl_id
           where repl_id - id which can use to take the replica set
        """
        logger.info("create new replica set")
        print locals()
        logger.info("members: {members}, auth_key={auth_key}, timeout={timeout}".format(**locals()))
        repl = ReplicaSet(members, auth_key)
        self[repl.repl_id] = repl
        return repl.repl_id

    def rs_info(self, repl_id):
        logger.info("get info about replica {repl_id}".format(**locals()))
        """return information about replica set
        Args:
            repl_id - replica set identity
        """
        return self[repl_id].rs_info()

    def rs_primary(self, repl_id):
        logger.info("find primary member for replica {repl_id}".format(**locals()))
        """find and return primary hostname
        Args:
            repl_id - replica set identity
        """
        repl = self[repl_id]
        primary = repl.primary()
        return repl.member_info(repl.host2id(primary))

    def rs_del(self, repl_id):
        logger.info("remove replica set {repl_id}".format(**locals()))
        """remove replica set with kill members
        Args:
            repl_id - replica set identity
        """
        repl = self._storage.pop(repl_id)
        repl.cleanup()
        del(repl)

    def rs_members(self, repl_id):
        logger.info("get members for replica {repl_id}".format(**locals()))
        """return list of replica set members
        Args:
            repl_id - replica set identity
        """
        return self[repl_id].members()

    def rs_member_info(self, repl_id, member_id):
        """return information about member
        Args:
            repl_id - replica set identity
            member_id - member index
        """
        logger.info("get info about member '{member_id}', repl: {repl_id}".format(**locals()))
        return self[repl_id].member_info(member_id)

    def rs_member_del(self, repl_id, member_id):
        """remove member from replica set (reconfig replica)
        Args:
            repl_id - replica set identity
            member_id - member index
        """
        logger.info("remove member '{member_id} from replica set {repl_id}".format(**locals()))
        repl = self[repl_id]
        result = repl.member_del(member_id)
        self[repl_id] = repl
        return result

    def rs_member_add(self, repl_id, params):
        """create instance and add it to existing replcia
        Args:
            repl_id - replica set identity
            params - member params
        """
        logger.info("create and add new member to replica set {repl_id}".format(**locals()))
        repl = self[repl_id]
        result = repl.repl_add_member(params)
        self[repl_id] = repl
        return result

    def rs_member_command(self, repl_id, member_id, command):
        """apply command(start, stop, restart) to member of replica set
        Args:
            repl_id - replica set identity
            member_id - member index
            command - command: start, stop, restart
        return command result as bool
        """
        logger.info("member '{member_id}' execute command '{command}'".format(**locals()))
        repl = self[repl_id]
        result = repl.member_command(member_id, command)
        self[repl_id] = repl
        return result

    def rs_member_update(self, repl_id, member_id, params):
        """apply new params to replica set member
        Args:
            repl_id - replica set identity
            member_id - member index
            params - new member's params
        return bool result of command
        """
        logger.info("update member '{member_id} , params: '{params}'".format(**locals()))
        repl = self[repl_id]
        result = repl.member_update(member_id, params)
        self[repl_id] = repl
        return result


class ReplicaSet(object):
    """class represents ReplicaSet"""

    hosts = Hosts()

    def __init__(self, members, auth_key=None):
        """create replica set according members config
        Args:
            members : list of members config
            auth_key: authorisation key
        """
        logger.info("init new replica set".format(**locals()))
        self.host_map = {}
        self.auth_key = auth_key
        self.repl_id = "rs-" + str(uuid4())
        config = {"_id": self.repl_id, "members": [
            self.member_create(member, index) for index, member in enumerate(members)
        ]}
        self.repl_init(config)  # TODO: kill if returned False

    def __len__(self):
        return len(self.host_map)

    def cleanup(self):
        """remove all members without reconfig"""
        for i in xrange(len(self)):
            self.member_del(i, reconfig=False)

    def id2host(self, member_id):
        return self.host_map[member_id]

    def host2id(self, hostname):
        for key, value in self.host_map.items():
            if value == hostname:
                return key

    def get_init_host(self, config):
        """return hostname which can init replica"""
        logger.info("find init host".format(**locals()))
        return [member['host'] for member in config['members']
                if not (member.get('arbiterOnly', False) or member.get('priority', 1) == 0)][0]

    def repl_init(self, config, reconfig=False):
        """init replica set by config
        Args:
            config - replica set config
            reconfig - is need reconfig replica set
        """
        logger.info("old host_map: {self.host_map}".format(**locals()))
        self.host_map = dict([(member['_id'], member['host']) for member in config['members']])
        logger.info("new host_map {self.host_map}".format(**locals()))
        if reconfig:
            host = self.primary()
            # host = self.get_init_host(config)
            command = 'replSetReconfig'
            config['version'] += 1
        else:
            host = self.get_init_host(config)
            command = 'replSetInitiate'
        logger.info("apply '{command}' with config {config} to replica set".format(**locals()))
        try:
            # print self.connection(host).admin.command(command, config)
            pymongo.Connection(host).admin.command(command, config)
        except (pymongo.errors.AutoReconnect):
            if reconfig:
                return self.__waiting_while_started(self.get_init_host(config))
            raise
        except pymongo.errors.OperationFailure:
            raise
        # waiting while replica set starts
        return self.__waiting_while_started(self.get_init_host(config))

    def run_command(self, command, arg=None, is_eval=False, member_id=None, slave_okay=True):
        """run command on replica set
        Args:
            command - command string
            arg - command argument
            is_eval - if True execute command as eval
            member_id - if is not None: run command on specific member
        return command result
        """
        logger.info("run admin command: '{command}', member_id: {member_id}, slave_okay: {slave_okay}".format(**locals()))
        executor = 'command'
        if is_eval:
            executor = 'eval'
        if arg:
            return getattr(self.connection(member_id).admin, executor)(command, arg)
        else:
            return getattr(self.connection(member_id).admin, executor)(command)

    def repl_config(self):
        logger.info("return replica config (using rs.conf())")
        return self.run_command("rs.conf()", member_id=self.host2id(self.primary()), is_eval=True, slave_okay=False)

    def member_create(self, params, member_id):
        """start new mongod instances as part of replica set
        Args:
            params - member params
            member_id - member index
        return member config as dict
        """
        logger.info("create new mongod instance: params: {params}, member_id: {member_id}".format(**locals()))
        member_config = params.get('rsParams', {})
        proc_params = {'replSet': self.repl_id}
        proc_params.update(params.get('procParams', {}))
        host_id = self.hosts.h_new('mongod', proc_params, self.auth_key)
        member_config.update({"_id": member_id, "host": self.hosts.h_info(host_id)['uri']})
        return member_config

    def repl_add_member(self, params):
        """create and add member to replica set with reconfig"""
        logger.info("add new member to replica set")
        repl_config = self.repl_config()
        member_config = self.member_create(params, len(repl_config['members']))
        repl_config['members'].append(member_config)
        return self.repl_init(repl_config, reconfig=True)

    def member_del(self, member_id, reconfig=True):
        """remove member from replica set
        Args:
            member_id - member index
            reconfig - is need reconfig
        """
        logger.info("remove member '{member_id}', reconfig={reconfig}".format(**locals()))
        host_id = self.hosts.h_id_by_hostname(self.id2host(member_id))
        self.hosts.h_del(host_id)
        result = True
        if reconfig:
            config = self.repl_config()
            config['members'].pop(member_id)
            return self.repl_init(config, True)
        return result

    def member_update(self, member_id, params):
        """update member's values with reconfig replica
        Args:
            member_id - member index
            params - updates member params
        """
        logger.info("update member '{member_id}' params: {params}".format(**locals()))
        config = self.repl_config()
        config['members'][member_id].update(params.get("rsParams", {}))
        return self.repl_init(config, True)

    def member_info(self, member_id):
        """return information about member"""
        logger.info("get information about member_id '{member_id}'".format(**locals()))
        host_info = self.hosts.h_info(self.hosts.h_id_by_hostname(self.id2host(member_id)))
        result = {'_id': member_id, 'uri': host_info['uri'], 'rsInfo': {}, 'procInfo': host_info['procInfo'], 'statuses': host_info['statuses']}
        repl = self.run_command('serverStatus', arg=None, is_eval=False, member_id=member_id)['repl']
        for key in ('votes', 'arbiterOnly', 'buildIndexes', 'hidden', 'priority', 'slaveDelay', 'votes', 'secondary'):
            if key in repl:
                result['rsInfo'][key] = repl[key]
        result['rsInfo']['primary'] = (repl['ismaster'] == True)
        return result

    def member_command(self, member_id, command):
        """apply command (start/stop/restart) to member instance of replica set
        Args:
            member_id - member index
            command - string command (start/stop/restart)
        return command's result
        """
        host_id = self.hosts.h_id_by_hostname(self.id2host(member_id))
        return self.hosts[host_id].h_command(command)

    def members(self):
        """return list of members information"""
        logger.info("get all members".format(**locals()))
        result = list()
        for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']:
            result.append({"_id": member['_id'], "host": member["name"]})
        return result
        # return [self.member_info(member['_id']) for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']]

    def rs_info(self):
        """return information about replica set"""
        logger.info("get info about replica set".format(**locals()))
        return {"id": self.repl_id, "auth_key": self.auth_key, "members": self.members()}

    def primary(self):
        """return primary hostname of replica set"""
        logger.info("find primary member".format(**locals()))
        try:
            primary = self.get_members_in_state(1)[0]
            logger.info("primary is {primary}".format(**locals()))
            return primary
        except IndexError:
            logger.info("primary member not found".format(**locals()))
            return None

    def get_members_in_state(self, state):
        """return all members of replica set in specific state"""
        logger.info("find members with state '{state}'".format(**locals()))
        members = self.run_command(command='replSetGetStatus', is_eval=False)['members']
        return [member['name'] for member in members if member['state'] == state]

    def connection(self, member_id=None, slave_okay=True):
        """return connection object to member(if specify) or primary
        Args:
            member_id - member index
            slave_okay - connection options
        return Connection object
        """
        logger.info("create connection object".format(**locals()))
        if member_id is not None:
            host = self.id2host(member_id)
            logger.info("use host '{host}' for connection".format(**locals()))
            return pymongo.Connection(host, slave_okay)
        else:
            # host = self.primary()
        # return pymongo.Connection(host, slave_okay)
            for host in self.host_map.values():
                logger.info("try take connection using host '{host}' for connection".format(**locals()))
                try:
                    return pymongo.Connection(host, slave_okay)
                except pymongo.errors.AutoReconnect:
                    continue

    def __waiting_while_started(self, primary, timeout=300):
        """waiting while replica set is started"""
        logger.info("waiting while replica started/restarted".format(**locals()))
        t_start = time.time()
        while True:
            try:
                members = [member for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']]
                if len(members) == len(filter(lambda member: member['state'] in (1, 2, 3, 7) and member['health'] == 1, members)):
                    logger.info("replica started".format(**locals()))
                    return True
                raise pymongo.errors.OperationFailure
            except (pymongo.errors.OperationFailure, TypeError):
                if time.time() - t_start > timeout:
                    logger.info("replica not started".format(**locals()))
                    return False
                logger.info("sleep 20 seconds".format(**locals()))
                time.sleep(20)
            except Exception as err:
                print repr(err)
                raise
