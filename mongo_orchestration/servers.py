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

import errno
import logging
import os
import platform
import re
import subprocess
import tempfile
import time

from uuid import uuid4

import pymongo

from mongo_orchestration import process
from mongo_orchestration.common import (
    BaseModel, DEFAULT_SUBJECT, DEFAULT_SSL_OPTIONS, connected, LOG_FILE)
from mongo_orchestration.compat import reraise
from mongo_orchestration.errors import ServersError, TimeoutError
from mongo_orchestration.singleton import Singleton
from mongo_orchestration.container import Container

logger = logging.getLogger(__name__)


class Server(BaseModel):
    """Class Server represents behaviour of  mongo instances """

    # redirect stdout to /dev/null?
    silence_stdout = True

    # default params for all mongo instances
    mongod_default = {"oplogSize": 100}

    # regular expression matching MongoDB versions
    version_patt = re.compile(
        '(?:db version v|MongoS version |mongos db version )'
        '(?P<version>(\d+\.)+\d+)')

    def __init_db(self, dbpath):
        if not dbpath:
            dbpath = tempfile.mkdtemp(prefix="mongo-")
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        return dbpath

    def __init_logpath(self, log_path):
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def __init_test_commands(self, config):
        """Conditionally enable test commands in the Server's config file."""
        if self.version >= (2, 4):
            params = config.get('setParameter', {})
            params['enableTestCommands'] = 1
            config['setParameter'] = params

    def __init_mongod(self, params, add_auth=False):
        cfg = self.mongod_default.copy()
        cfg.update(params)

        # create db folder
        cfg['dbpath'] = self.__init_db(cfg.get('dbpath', None))

        if add_auth:
            cfg['auth'] = True
            if self.auth_key:
                cfg['keyFile'] = self.key_file

        # create logpath: goes in dbpath by default under process name + ".log"
        logpath = cfg.setdefault(
            'logpath', os.path.join(cfg['dbpath'], 'mongod.log'))
        self.__init_logpath(logpath)

        # find open port
        if 'port' not in cfg:
            cfg['port'] = process.PortPool().port(check=True)

        self.__init_test_commands(cfg)

        return process.write_config(cfg), cfg

    def __init_mongos(self, params):
        cfg = params.copy()

        log_path = cfg.setdefault(
            'logpath',
            os.path.join(tempfile.mkdtemp(prefix='mongo-'), 'mongos.log'))
        self.__init_logpath(log_path)

        # use keyFile
        if self.auth_key:
            cfg['keyFile'] = self.key_file

        if 'port' not in cfg:
            cfg['port'] = process.PortPool().port(check=True)

        self.__init_test_commands(cfg)

        return process.write_config(cfg), cfg

    def __init__(self, name, procParams, sslParams={}, auth_key=None,
                 login='', password='', auth_source='admin'):
        """Args:
            name - name of process (mongod or mongos)
            procParams - dictionary with params for mongo process
            auth_key - authorization key
            login - username for the  admin collection
            password - password
        """
        logger.debug("Server.__init__({name}, {procParams}, {sslParams}, {auth_key}, {login}, {password})".format(**locals()))
        self.name = name  # name of process
        self.login = login
        self.auth_source = auth_source
        self.password = password
        self.auth_key = auth_key
        self.pid = None  # process pid
        self.proc = None # Popen object
        self.host = None  # hostname without port
        self.hostname = None  # string like host:port
        self.is_mongos = False
        self.kwargs = {}
        self.ssl_params = sslParams
        self.restart_required = self.login or self.auth_key

        if self.ssl_params:
            self.kwargs.update(DEFAULT_SSL_OPTIONS)

        proc_name = os.path.split(name)[1].lower()
        procParams.update(sslParams)
        if proc_name.startswith('mongod'):
            self.config_path, self.cfg = self.__init_mongod(procParams)

        elif proc_name.startswith('mongos'):
            self.is_mongos = True
            self.config_path, self.cfg = self.__init_mongos(procParams)

        else:
            self.config_path, self.cfg = None, {}

        self.port = self.cfg.get('port', None)  # connection port

    @property
    def connection(self):
        """return authenticated connection"""
        c = pymongo.MongoClient(
            self.hostname, fsync=True,
            socketTimeoutMS=self.socket_timeout, **self.kwargs)
        connected(c)
        if not self.is_mongos and self.login and not self.restart_required:
            db = c[self.auth_source]
            if self.x509_extra_user:
                auth_dict = {
                    'name': DEFAULT_SUBJECT, 'mechanism': 'MONGODB-X509'}
            else:
                auth_dict = {'name': self.login, 'password': self.password}
            try:
                db.authenticate(**auth_dict)
            except:
                logger.exception("Could not authenticate to %s with %r"
                                 % (self.hostname, auth_dict))
                raise
        return c

    @property
    def version(self):
        """Get the version of MongoDB that this Server runs as a tuple."""
        command = (self.name, '--version')
        stdout, _ = subprocess.Popen(
            command, stdout=subprocess.PIPE).communicate()
        first_line = str(stdout).split('\n')[0]
        match = re.search(self.version_patt, first_line)
        version_string = match.group('version')
        return tuple(map(int, version_string.split('.')))

    def freeze(self, timeout=60):
        """Run `replSetFreeze` on this server.

        May raise `pymongo.errors.OperationFailure` if this server is not a
        replica set member.
        """
        return self.run_command('replSetFreeze', timeout)

    def stepdown(self, timeout=60):
        """Run `replSetStepDown` on this server.

        May raise `pymongo.errors.OperationFailure` if this server is not a
        replica set member.
        """
        try:
            self.run_command('replSetStepDown', timeout)
        except pymongo.errors.AutoReconnect:
            pass

    def run_command(self, command, arg=None, is_eval=False):
        """run command on the server

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
        return process.proc_alive(self.proc)

    def info(self):
        """return info about server as dict object"""
        proc_info = {"name": self.name,
                     "params": self.cfg,
                     "alive": self.is_alive,
                     "optfile": self.config_path}
        if self.is_alive:
            proc_info['pid'] = self.proc.pid
        logger.debug("proc_info: {proc_info}".format(**locals()))
        mongodb_uri = ''
        server_info = {}
        status_info = {}
        if self.hostname and self.cfg.get('port', None):
            try:
                c = self.connection
                server_info = c.server_info()
                logger.debug("server_info: {server_info}".format(**locals()))
                mongodb_uri = 'mongodb://' + self.hostname
                status_info = {"primary": c.is_primary, "mongos": c.is_mongos, "locked": c.is_locked}
                logger.debug("status_info: {status_info}".format(**locals()))
            except (pymongo.errors.AutoReconnect, pymongo.errors.OperationFailure, pymongo.errors.ConnectionFailure):
                server_info = {}
                status_info = {}

        result = {"mongodb_uri": mongodb_uri, "statuses": status_info,
                  "serverInfo": server_info, "procInfo": proc_info,
                  "orchestration": 'servers'}
        if self.login:
            result['mongodb_auth_uri'] = self.mongodb_auth_uri(self.hostname)
        logger.debug("return {result}".format(result=result))
        return result

    @property
    def _is_locked(self):
        lock_file = os.path.join(self.cfg['dbpath'], 'mongod.lock')
        # If neither journal nor nojournal is specified, assume nojournal=True
        journaling_enabled = (self.cfg.get('journal') or
                              not self.cfg.get('nojournal', True))
        try:
            with open(lock_file, 'r') as fd:
                return (not journaling_enabled and len(fd.read())) > 0
        except IOError as e:
            # Permission denied -- mongod holds the lock on the file.
            if platform.system() == 'Windows' and e.errno == errno.EACCES:
                return True
        return False

    def start(self, timeout=300):
        """start server
        return True of False"""
        if self.is_alive:
            return True
        try:
            if self.cfg.get('dbpath', None) and self._is_locked:
                # repair if needed
                process.repair_mongo(self.name, self.cfg['dbpath'])

            self.proc, self.hostname = process.mprocess(
                self.name, self.config_path, self.cfg.get('port', None),
                timeout, self.silence_stdout)
            self.pid = self.proc.pid
            logger.debug("pid={pid}, hostname={hostname}".format(pid=self.pid, hostname=self.hostname))
            self.host = self.hostname.split(':')[0]
            self.port = int(self.hostname.split(':')[1])

            # Wait for Server to respond to isMaster.
            for i in range(timeout):
                try:
                    self.run_command('isMaster')
                    break
                except pymongo.errors.ConnectionFailure:
                    time.sleep(0.1)
            else:
                raise TimeoutError(
                    "Server did not respond to 'isMaster' after %d attempts."
                    % timeout)
        except (OSError, TimeoutError):
            logpath = self.cfg.get('logpath')
            if logpath:
                # Copy the server logs into the mongo-orchestration logs.
                logger.error(
                    "Could not start Server. Please find server log below.\n"
                    "=====================================================")
                with open(logpath) as lp:
                    logger.error(lp.read())
            else:
                logger.exception(
                    'Could not start Server, and no logpath was provided!')
            reraise(TimeoutError,
                    'Could not start Server. '
                    'Please check server log located in ' +
                    self.cfg.get('logpath', '<no logpath given>') +
                    ' or the mongo-orchestration log in ' +
                    LOG_FILE + ' for more details.')
        if self.restart_required:
            if self.login:
                # Add users to the appropriate database.
                self._add_users()
            self.stop()

            # Restart with keyfile and auth.
            if self.is_mongos:
                self.config_path, self.cfg = self.__init_mongos(self.cfg)
            else:
                # Add auth options to this Server's config file.
                self.config_path, self.cfg = self.__init_mongod(
                    self.cfg, add_auth=True)
            self.restart_required = False
            self.start()

        return True

    def stop(self):
        """stop server"""
        return process.kill_mprocess(self.proc)

    def restart(self, timeout=300, config_callback=None):
        """restart server: stop() and start()
        return status of start command
        """
        self.stop()
        if config_callback:
            self.cfg = config_callback(self.cfg.copy())
        self.config_path = process.write_config(self.cfg)
        return self.start(timeout)

    def reset(self):
        """Ensure Server has started and responds to isMaster."""
        self.start()
        return self.info()

    def _add_users(self):
        try:
            # Determine authentication mechanisms.
            set_params = self.cfg.get('setParameter', {})
            auth_mechs = set_params.get(
                'authenticationMechanisms', '').split(',')

            # We need to add an additional user if MONGODB-X509 is the only auth
            # mechanism.
            self.x509_extra_user = False
            if len(auth_mechs) == 1 and auth_mechs[0] == 'MONGODB-X509':
                self.x509_extra_user = True

            super(Server, self)._add_users(self.connection[self.auth_source])
        except pymongo.errors.OperationFailure as e:
            logger.error("Error: {0}".format(e))
            # user added successfuly but OperationFailure exception raises
            pass

    def cleanup(self):
        """remove server data"""
        process.cleanup_mprocess(self.config_path, self.cfg)


class Servers(Singleton, Container):
    """ Servers is a dict-like collection for Server objects"""
    _name = 'servers'
    _obj_type = Server
    releases = {}
    pids_file = tempfile.mktemp(prefix="mongo-")

    def __getitem__(self, key):
        return self.info(key)

    def cleanup(self):
        """remove all servers with their data"""
        for server_id in self:
            self.remove(server_id)

    def create(self, name, procParams, sslParams={},
               auth_key=None, login=None, password=None,
               auth_source='admin', timeout=300, autostart=True,
               server_id=None, version=None):
        """create new server
        Args:
           name - process name or path
           procParams - dictionary with specific params for instance
           auth_key - authorization key
           login - username for the  admin collection
           password - password
           timeout -  specify how long, in seconds, a command can take before times out.
           autostart - (default: True), autostart instance
        Return server_id
           where server_id - id which can use to take the server from servers collection
        """
        name = os.path.split(name)[1]
        if server_id is None:
            server_id = str(uuid4())
        if server_id in self:
            raise ServersError("Server with id %s already exists." % server_id)

        bin_path = self.bin_path(version)
        server = Server(os.path.join(bin_path, name), procParams, sslParams,
                        auth_key, login, password, auth_source)
        if autostart:
            server.start(timeout)
        self[server_id] = server
        return server_id

    def restart(self, server_id, timeout=300, config_callback=None):
        self._storage[server_id].restart(timeout, config_callback)

    def remove(self, server_id):
        """remove server and data stuff
        Args:
            server_id - server identity
        """
        server = self._storage.pop(server_id)
        server.stop()
        server.cleanup()

    def db_command(self, server_id, command, arg=None, is_eval=False):
        server = self._storage[server_id]
        result = server.run_command(command, arg, is_eval)
        self._storage[server_id] = server
        return result

    def command(self, server_id, command, *args):
        """run command
        Args:
            server_id - server identity
            command - command which apply to server
        """
        server = self._storage[server_id]
        try:
            if args:
                result = getattr(server, command)(*args)
            else:
                result = getattr(server, command)()
        except AttributeError:
            raise ValueError("Cannot issue the command %r to server %s"
                             % (command, server_id))
        self._storage[server_id] = server
        return result

    def info(self, server_id):
        """return dicionary object with info about server
        Args:
            server_id - server identity
        """
        result = self._storage[server_id].info()
        result['id'] = server_id
        return result

    def hostname(self, server_id):
        return self._storage[server_id].hostname

    def host_to_server_id(self, hostname):
        for server_id in self._storage:
            if self._storage[server_id].hostname == hostname:
                return server_id

    def is_alive(self, server_id):
        return self._storage[server_id].is_alive
