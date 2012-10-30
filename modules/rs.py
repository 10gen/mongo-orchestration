# coding=utf-8
import logging
logger = logging.getLogger(__name__)
from uuid import uuid4
from singleton import Singleton
from storage import Storage
import pymongo
from hosts import Hosts
import time
import errors


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

    def rs_new(self, rs_params):
        """create new replica set
        Args:
           rs_params - replica set configuration
           members - list of members params
           auth_key - authorization key
           timeout -  specify how long, in seconds, a command can take before times out.
        Return repl_id
           where repl_id - id which can use to take the replica set
        """
        repl_id = rs_params.get('id', None)
        if repl_id is not None and repl_id in self:
            raise errors.ReplicaSetError("replica set with id={id} already exists".format(id=repl_id))
        repl = ReplicaSet(rs_params)
        self[repl.repl_id] = repl
        return repl.repl_id

    def repl_info(self, repl_id):
        logger.info("get info about replica {repl_id}".format(**locals()))
        """return information about replica set
        Args:
            repl_id - replica set identity
        """
        return self[repl_id].repl_info()

    def rs_primary(self, repl_id):
        logger.info("find primary member for replica {repl_id}".format(**locals()))
        """find and return primary hostname
        Args:
            repl_id - replica set identity
        """
        repl = self[repl_id]
        primary = repl.primary()
        return repl.member_info(repl.host2id(primary))

    def rs_primary_stepdown(self, repl_id, timeout=60):
        repl = self[repl_id]
        return repl.stepdown(timeout)

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

    def rs_secondaries(self, repl_id):
        return self[repl_id].secondaries()

    def rs_arbiters(self, repl_id):
        return self[repl_id].arbiters()

    def rs_hidden(self, repl_id):
        return self[repl_id].hidden()

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
        result = repl.repl_member_add(params)
        self[repl_id] = repl
        return result

    def rs_member_command(self, repl_id, member_id, command):
        """apply command(start, stop, restart) to the member of replica set
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

    def __init__(self, rs_params):
        """create replica set according members config
        Args:
            members : list of members config
            auth_key: authorisation key
        """
        self.host_map = {}
        self.auth_key = rs_params.get('auth_key', None)
        self.repl_id = rs_params.get('id', None) or "rs-" + str(uuid4())
        config = {"_id": self.repl_id, "members": [
            self.member_create(member, index) for index, member in enumerate(rs_params.get('members', {}))
        ]}
        if not self.repl_init(config):
            self.cleanup()
            raise errors.ReplicaSetError("replica can't started")

    def __len__(self):
        return len(self.host_map)

    def cleanup(self):
        """remove all members without reconfig"""
        for item in self.host_map:
            self.member_del(item, reconfig=False)

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
        c = pymongo.Connection(init_host)
        c.admin.command("replSetInitiate", config)
        # wait while real state equals config
        return self.waiting_config_state()

    def repl_update(self, config):
        """reconfig replica set
        return True if reconfig successfuly, else False"""
        config['version'] += 1
        try:
            self.run_command("replSetReconfig", config)
            self.update_host_map(config)
        except pymongo.errors.AutoReconnect:
            pass
        self.waiting_config_state()
        return self.connection() and True

    def repl_info(self):
        """return information about replica set"""
        return {"id": self.repl_id, "auth_key": self.auth_key, "members": self.members()}

    def repl_member_add(self, params):
        """create new mongod instances and add it to the replica set."""
        repl_config = self.config
        member_config = self.member_create(params, len(repl_config['members']))
        repl_config['members'].append(member_config)
        return self.repl_update(repl_config)

    def run_command(self, command, arg=None, is_eval=False, member_id=None):
        """run command on replica set
        Args:
            command - command string
            arg - command argument
            is_eval - if True execute command as eval
            member_id - member id
        return command result
        """
        mode = is_eval and 'eval' or 'command'
        return getattr(self.connection(member_id=member_id).admin, mode)(command, arg)

    @property
    def config(self):
        """return replica set config, use rs.conf() command"""
        return self.run_command("rs.conf()", is_eval=True)

    def member_create(self, params, member_id):
        """start new mongod instances as part of replica set
        Args:
            params - member params
            member_id - member index
        return member config as dict
        """
        member_config = params.get('rsParams', {})
        proc_params = {'replSet': self.repl_id}
        proc_params.update(params.get('procParams', {}))
        host_id = self.hosts.h_new('mongod', proc_params, self.auth_key)
        member_config.update({"_id": member_id, "host": self.hosts.h_info(host_id)['uri']})
        return member_config

    def member_del(self, member_id, reconfig=True):
        """remove member from replica set
        Args:
            member_id - member index
            reconfig - is need reconfig
        """
        host_id = self.hosts.h_id_by_hostname(self.id2host(member_id))
        if reconfig:
            config = self.config
            config['members'].pop(member_id)
            self.repl_update(config)
        self.hosts.h_del(host_id)
        return True

    def member_update(self, member_id, params):
        """update member's values with reconfig replica
        Args:
            member_id - member index
            params - updates member params
        """
        config = self.config
        config['members'][member_id].update(params.get("rsParams", {}))
        self.repl_update(config)

    def member_info(self, member_id):
        """return information about member"""
        host_info = self.hosts.h_info(self.hosts.h_id_by_hostname(self.id2host(member_id)))
        result = {'_id': member_id, 'uri': host_info['uri'], 'rsInfo': {}, 'procInfo': host_info['procInfo'], 'statuses': host_info['statuses']}
        result['rsInfo'] = {}
        if host_info['procInfo']['alive']:
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
        return self.hosts.h_command(host_id, command)

    def members(self):
        """return list of members information"""
        result = list()
        for member in self.run_command(command="replSetGetStatus", is_eval=False)['members']:
            result.append({"_id": member['_id'], "host": member["name"]})
        return result

    def stepdown(self, timeout=60):
        try:
            self.run_command("replSetStepDown", is_eval=False)
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

    def connection(self, member_id=None, read_preference=pymongo.ReadPreference.PRIMARY, timeout=300):
        """return ReplicaSetConnection object"""
        t_start = time.time()
        hosts = member_id is not None and self.id2host(member_id) or ",".join(self.host_map.values())
        while True:
            try:
                if member_id is None:
                    c = pymongo.ReplicaSetConnection(hosts, replicaSet=self.repl_id, read_preference=read_preference)
                    if c.primary:
                        return c
                    raise pymongo.errors.AutoReconnect("No replica set primary available")
                else:
                    c = pymongo.Connection(hosts, read_preference=read_preference)
                    return c
            except (pymongo.errors.PyMongoError):
                if time.time() - t_start > timeout:
                    return False
                time.sleep(20)

    def secondaries(self):
        return [{"_id": self.host2id(member), "host": member} for member in self.get_members_in_state(2)]

    def arbiters(self):
        return [{"_id": self.host2id(member), "host": member} for member in self.get_members_in_state(7)]

    def hidden(self):
        members = [self.member_info(item["_id"]) for item in self.members()]
        return [{"_id": member['_id'], "host": member['uri']} for member in members if member['rsInfo'].get('hidden', False)]

    def waiting_config_state(self, timeout=300):
        t_start = time.time()
        while not self.check_config_state():
            if time.time() - t_start > timeout:
                return False
            time.sleep(20)
        return True

    def check_config_state(self):
        "check is real state equal config"
        # TODO: fix issue hidden=true -> hidden=false
        config = self.config
        for member in config['members']:
            member.pop('host')
            'priority' in member and member.pop('priority')
            real_info = {"_id": member["_id"]}
            real_info.update(self.member_info(member["_id"])['rsInfo'])
            for key in member:
                if member[key] != real_info.get(key, None):
                    return False
        return True
