#!/usr/bin/python
# coding=utf-8

import logging
logger = logging.getLogger(__name__)
import lib.process
from uuid import uuid4
from lib.singleton import Singleton
from lib.container import Container
import pymongo
import os
import tempfile
import stat


class Host(object):
    """Class Host represents behaviour of  mongo instances """

    # default params for all mongo instances
    mongod_default = {"noprealloc": True, "smallfiles": True, "oplogSize": 10}

    def __init_db(self, dbpath):
        if not dbpath:
            dbpath = tempfile.mkdtemp(prefix="mongo-")
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        return dbpath

    def __init_auth_key(self, auth_key, folder):
        key_file = os.path.join(os.path.join(folder, 'key'))
        open(key_file, 'w').write(auth_key)
        os.chmod(key_file, stat.S_IRUSR)
        return key_file

    def __init_logpath(self, log_path):
        if log_path and not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(log_path)

    def __init_mongod(self, params, ssl):
        cfg = self.mongod_default.copy()
        cfg.update(params)
        cfg.update(ssl)

        # create db folder
        cfg['dbpath'] = self.__init_db(cfg.get('dbpath', None))

        # use keyFile
        if self.auth_key:
            cfg['auth'] = True
            cfg['keyFile'] = self.__init_auth_key(self.auth_key, cfg['dbpath'])

        if self.login:
            cfg['auth'] = True

        # create logpath
        self.__init_logpath(cfg.get('logpath', None))

        # find open port
        if 'port' not in cfg:
            cfg['port'] = lib.process.PortPool().port(check=True)

        return lib.process.write_config(cfg), cfg

    def __init_mongos(self, params, ssl):
        cfg = params.copy()
        cfg.update(ssl)

        self.__init_logpath(cfg.get('logpath', None))

        # use keyFile
        if self.auth_key:
            cfg['keyFile'] = self.__init_auth_key(self.auth_key, tempfile.mkdtemp())

        if 'port' not in cfg:
            cfg['port'] = lib.process.PortPool().port(check=True)

        return lib.process.write_config(cfg), cfg

    def __init__(self, name, procParams, sslParams={}, auth_key=None, login='', password=''):
        """Args:
            name - name of process (mongod or mongos)
            procParams - dictionary with params for mongo process
            auth_key - authorization key
            login - username for the  admin collection
            password - password
        """
        logger.debug("Host.__init__({name}, {procParams}, {sslParams}, {auth_key}, {login}, {password})".format(**locals()))
        self.name = name  # name of process
        self.login = login
        self.password = password
        self.auth_key = auth_key
        self.admin_added = False
        self.pid = None  # process pid
        self.proc = None # Popen object
        self.host = None  # hostname without port
        self.hostname = None  # string like host:port
        self.is_mongos = False
        self.kwargs = {}

        if not not sslParams:
            self.kwargs['ssl'] = True

        proc_name = os.path.split(name)[1].lower()
        if proc_name.startswith('mongod'):
            self.config_path, self.cfg = self.__init_mongod(procParams, sslParams)

        elif proc_name.startswith('mongos'):
            self.is_mongos = True
            self.config_path, self.cfg = self.__init_mongos(procParams, sslParams)

        else:
            self.config_path, self.cfg = None, {}

        self.port = self.cfg.get('port', None)  # connection port

    @property
    def connection(self):
        """return authenticated connection"""
        c = pymongo.MongoClient(self.hostname, **self.kwargs)
        if not self.is_mongos and self.admin_added and (self.login and self.password):
            try:
                c.admin.authenticate(self.login, self.password)
            except:
                pass
        return c

    def run_command(self, command, arg=None, is_eval=False):
        """run command on the host

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

        result = getattr(self.connection.admin, mode)(command, name, **d)
        return result

    @property
    def is_alive(self):
        return lib.process.proc_alive(self.proc)

    def info(self):
        """return info about host as dict object"""
        proc_info = {"name": self.name, "params": self.cfg, "alive": self.is_alive,
                     "pid": self.pid if self.proc else None,
                     "optfile": self.config_path}
        logger.debug("proc_info: {proc_info}".format(**locals()))
        server_info = {}
        status_info = {}
        if self.hostname and self.cfg.get('port', None):
            try:
                c = pymongo.MongoClient(self.hostname.split(':')[0], self.cfg['port'], socketTimeoutMS=120000, **self.kwargs)
                server_info = c.server_info()
                logger.debug("server_info: {server_info}".format(**locals()))
                status_info = {"primary": c.is_primary, "mongos": c.is_mongos, "locked": c.is_locked}
                logger.debug("status_info: {status_info}".format(**locals()))
            except (pymongo.errors.AutoReconnect, pymongo.errors.OperationFailure, pymongo.errors.ConnectionFailure):
                server_info = {}
                status_info = {}

        logger.debug("return {d}".format(d={"uri": self.hostname, "statuses": status_info, "serverInfo": server_info, "procInfo": proc_info}))
        return {"uri": self.hostname, "statuses": status_info, "serverInfo": server_info, "procInfo": proc_info, "orchestration": 'hosts'}

    @property
    def _is_locked(self):
        lock_file = os.path.join(self.cfg['dbpath'], 'mongod.lock')
        # If neither journal nor nojournal is specified, assume nojournal=True
        journaling_enabled = (self.cfg.get('journal') or
                              not self.cfg.get('nojournal', True))
        return (not journaling_enabled and os.path.exists(lock_file) and len(open(lock_file, 'r').read())) > 0

    def start(self, timeout=300):
        """start host
        return True of False"""
        try:
            if self.cfg.get('dbpath', None) and self._is_locked:
                # repair if needed
                lib.process.repair_mongo(self.name, self.cfg['dbpath'])

            self.proc, self.hostname = lib.process.mprocess(self.name, self.config_path, self.cfg.get('port', None), timeout)
            self.pid = self.proc.pid
            logger.debug("pid={pid}, hostname={hostname}".format(pid=self.pid, hostname=self.hostname))
            self.host = self.hostname.split(':')[0]
            self.port = int(self.hostname.split(':')[1])
        except OSError as e:
            logger.error("Error: {0}".format(e))
            return False
        if not self.admin_added and self.login:
            self._add_auth()
            self.admin_added = True
        return True

    def stop(self):
        """stop host"""
        return lib.process.kill_mprocess(self.proc)

    def restart(self, timeout=300):
        """restart host: stop() and start()
        return status of start command
        """
        self.stop()
        return self.start(timeout)

    def _add_auth(self):
        try:
            db = self.connection.admin
            logger.debug("add admin user {login}/{password}".format(login=self.login, password=self.password))
            db.add_user(self.login, self.password,
                        roles=['__system',
                               'clusterAdmin',
                               'dbAdminAnyDatabase',
                               'readWriteAnyDatabase',
                               'userAdminAnyDatabase'])
            db.logout()
        except pymongo.errors.OperationFailure as e:
            logger.error("Error: {0}".format(e))
            # user added successfuly but OperationFailure exception raises
            pass

    def cleanup(self):
        """remove host data"""
        lib.process.cleanup_mprocess(self.config_path, self.cfg)


class Hosts(Singleton, Container):
    """ Hosts is a dict-like collection for Host objects"""
    _name = 'hosts'
    _obj_type = Host
    bin_path = ''
    pids_file = tempfile.mktemp(prefix="mongo-")

    def __getitem__(self, key):
        return self.info(key)

    def cleanup(self):
        """remove all hosts with their data"""
        if self._storage:
            for host_id in self._storage:
                self.remove(host_id)

    def create(self, name, procParams, sslParams={}, auth_key=None, login=None, password=None, timeout=300, autostart=True, host_id=None):
        """create new host
        Args:
           name - process name or path
           procParams - dictionary with specific params for instance
           auth_key - authorization key
           login - username for the  admin collection
           password - password
           timeout -  specify how long, in seconds, a command can take before times out.
           autostart - (default: True), autostart instance
        Return host_id
           where host_id - id which can use to take the host from hosts collection
        """
        name = os.path.split(name)[1]
        try:
            host = Host(os.path.join(self.bin_path, name), procParams, sslParams, auth_key, login, password)
            if host_id is None:
                host_id = str(uuid4())
            if autostart:
                if not host.start(timeout):
                    raise OSError
            self[host_id] = host
            return host_id
        except:
            raise

    def remove(self, host_id):
        """remove host and data stuff
        Args:
            host_id - host identity
        """
        host = self._storage.pop(host_id)
        host.stop()
        host.cleanup()

    def db_command(self, host_id, command, arg=None, is_eval=False):
        host = self._storage[host_id]
        result = host.run_command(command, arg, is_eval)
        self._storage[host_id] = host
        return result

    def command(self, host_id, command, *args):
        """run command
        Args:
            host_id - host identity
            command - command which apply to host
        """
        host = self._storage[host_id]
        try:
            if args:
                result = getattr(host, command)(args)
            else:
                result = getattr(host, command)()
        except AttributeError:
            raise ValueError
        self._storage[host_id] = host
        return result

    def info(self, host_id):
        """return dicionary object with info about host
        Args:
            host_id - host identity
        """
        result = self._storage[host_id].info()
        result['id'] = host_id
        return result

    def hostname(self, host_id):
        return self._storage[host_id].hostname

    def id_by_hostname(self, hostname):
        for host_id in self._storage:
            if self._storage[host_id].hostname == hostname:
                return host_id

    def is_alive(self, host_id):
        return self._storage[host_id].is_alive
