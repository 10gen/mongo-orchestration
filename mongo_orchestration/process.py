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
import json
import logging
import os
import platform
import shutil
import stat
import socket
import subprocess
import time
import tempfile

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

from bottle import request

from mongo_orchestration.common import DEFAULT_BIND
from mongo_orchestration.compat import reraise
from mongo_orchestration.errors import TimeoutError, RequestError
from mongo_orchestration.singleton import Singleton

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _host():
    """Get the Host from the most recent HTTP request."""
    host_and_port = request.urlparts[1]
    try:
        host, _ = host_and_port.split(':')
    except ValueError:
        # No port yet. Host defaults to '127.0.0.1' in bottle.request.
        return DEFAULT_BIND
    return host or DEFAULT_BIND


class PortPool(Singleton):

    __ports = set()
    __closed = set()
    __id = None

    def __init__(self, min_port=1025, max_port=2000, port_sequence=None):
        """
        Args:
            min_port - min port number  (ignoring if 'port_sequence' is not None)
            max_port - max port number  (ignoring if 'port_sequence' is not None)
            port_sequence - iterate sequence which contains numbers of ports
        """
        if not self.__id:  # singleton checker
            self.__id = id(self)
            self.__init_range(min_port, max_port, port_sequence)

    def __init_range(self, min_port=1025, max_port=2000, port_sequence=None):
        if port_sequence:
            self.__ports = set(port_sequence)
        else:
            self.__ports = set(range(min_port, max_port + 1))
        self.__closed = set()
        self.refresh()

    def __check_port(self, port):
        """check port status
        return True if port is free, False else
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((_host(), port))
            return True
        except socket.error:
            return False
        finally:
            s.close()

    def release_port(self, port):
        """release port"""
        if port in self.__closed:
            self.__closed.remove(port)
        self.__ports.add(port)

    def port(self, check=False):
        """return next opened port
        Args:
          check - check is port realy free
        """
        if not self.__ports:  # refresh ports if sequence is empty
            self.refresh()

        try:
            port = self.__ports.pop()
            if check:
                while not self.__check_port(port):
                    self.release_port(port)
                    port = self.__ports.pop()
        except (IndexError, KeyError):
            raise IndexError("Could not find a free port,\nclosed ports: {closed}".format(closed=self.__closed))
        self.__closed.add(port)
        return port

    def refresh(self, only_closed=False):
        """refresh ports status
        Args:
          only_closed - check status only for closed ports
        """
        if only_closed:
            opened = filter(self.__check_port, self.__closed)
            self.__closed = self.__closed.difference(opened)
            self.__ports = self.__ports.union(opened)
        else:
            ports = self.__closed.union(self.__ports)
            self.__ports = set(filter(self.__check_port, ports))
            self.__closed = ports.difference(self.__ports)

    def change_range(self, min_port=1025, max_port=2000, port_sequence=None):
        """change Pool port range"""
        self.__init_range(min_port, max_port, port_sequence)


def wait_for(port_num, timeout):
    """waits while process starts.
    Args:
        port_num    - port number
        timeout     - specify how long, in seconds, a command can take before times out.
    return True if process started, return False if not
    """
    logger.debug("wait for {port_num}".format(**locals()))
    t_start = time.time()
    sleeps = 0.1
    while time.time() - t_start < timeout:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((_host(), port_num))
                return True
            except (IOError, socket.error):
                time.sleep(sleeps)
        finally:
            s.close()
    return False


def repair_mongo(name, dbpath):
    """repair mongodb after usafe shutdown"""
    cmd = [name, "--dbpath", dbpath, "--repair"]
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    timeout = 30
    t_start = time.time()
    while time.time() - t_start < timeout:
        proc.stdout.flush()
        line = str(proc.stdout.readline())
        if "dbexit: really exiting now" in line:
            return
    return


def mprocess(name, config_path, port=None, timeout=180, silence_stdout=True):
    """start 'name' process with params from config_path.
    Args:
        name - process name or path
        config_path - path to file where should be stored configuration
        port - process's port
        timeout - specify how long, in seconds, a command can take before times out.
                  if timeout <=0 - doesn't wait for complete start process
        silence_stdout - if True (default), redirect stdout to /dev/null
    return tuple (Popen object, host) if process started, return (None, None) if not
    """

    logger.debug(
        "mprocess(name={name!r}, config_path={config_path!r}, port={port!r}, "
                 "timeout={timeout!r})".format(**locals()))
    if not (config_path and isinstance(config_path, str) and os.path.exists(config_path)):
        raise OSError("can't find config file {config_path}".format(**locals()))

    cfg = read_config(config_path)
    cmd = [name, "--config", config_path]

    if cfg.get('port', None) is None or port:
        port = port or PortPool().port(check=True)
        cmd.extend(['--port', str(port)])
    host = "{host}:{port}".format(host=_host(), port=port)
    try:
        logger.debug("execute process: %s", ' '.join(cmd))
        proc = subprocess.Popen(
            cmd,
            stdout=DEVNULL if silence_stdout else None,
            stderr=subprocess.STDOUT)

        if proc.poll() is not None:
            logger.debug("process is not alive")
            raise OSError("Process started, but died immediately.")
    except (OSError, TypeError) as err:
        message = "exception while executing process: {err}".format(err=err)
        logger.debug(message)
        raise OSError(message)
    if timeout > 0 and wait_for(port, timeout):
        logger.debug("process '{name}' has started: pid={proc.pid}, host={host}".format(**locals()))
        return (proc, host)
    elif timeout > 0:
        logger.debug("hasn't connected to pid={proc.pid} with host={host} during timeout {timeout} ".format(**locals()))
        logger.debug("terminate process with pid={proc.pid}".format(**locals()))
        kill_mprocess(proc)
        proc_alive(proc) and time.sleep(3)  # wait while process stoped
        message = ("Could not connect to process during "
                   "{timeout} seconds".format(timeout=timeout))
        raise TimeoutError(message, errno.ETIMEDOUT)
    return (proc, host)


def kill_mprocess(process):
    """kill process
    Args:
        process - Popen object for process
    """
    if process and proc_alive(process):
        process.terminate()
        process.communicate()
    return not proc_alive(process)


def cleanup_mprocess(config_path, cfg):
    """remove all process's stuff
    Args:
       config_path - process's options file
       cfg - process's config
    """
    for key in ('keyFile', 'logPath', 'dbpath'):
        remove_path(cfg.get(key, None))
    isinstance(config_path, str) and os.path.exists(config_path) and remove_path(config_path)


def remove_path(path):
    """remove path from file system
    If path is None - do nothing"""
    if path is None or not os.path.exists(path):
        return
    if platform.system() == 'Windows':
        # Need to have write permission before deleting the file.
        os.chmod(path, stat.S_IWRITE)
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            shutil.os.remove(path)
    except OSError:
        logger.exception("Could not remove path: %s" % path)


def write_config(params, config_path=None):
    """write mongo*'s config file
    Args:
       params - options wich file contains
       config_path - path to the config_file, will create if None
    Return config_path
       where config_path - path to mongo*'s options file
    """
    if config_path is None:
        config_path = tempfile.mktemp(prefix="mongo-")

    cfg = params.copy()
    if 'setParameter' in cfg:
        set_parameters = cfg.pop('setParameter')
        try:
            for key, value in set_parameters.items():
                cfg['setParameter = ' + key] = value
        except AttributeError:
            reraise(RequestError,
                    'Not a valid value for setParameter: %r '
                    'Expected "setParameter": {<param name> : value, ...}'
                    % set_parameters)

    # fix boolean value
    for key, value in cfg.items():
        if isinstance(value, bool):
            cfg[key] = json.dumps(value)

    with open(config_path, 'w') as fd:
        data = '\n'.join('%s=%s' % (key, item) for key, item in cfg.items())
        fd.write(data)
    return config_path


def read_config(config_path):
    """read config_path and return options as dictionary"""
    result = {}
    with open(config_path, 'r') as fd:
        for line in fd.readlines():
            if '=' in line:
                key, value = line.split('=', 1)
                try:
                    result[key] = json.loads(value)
                except ValueError:
                    result[key] = value.rstrip('\n')
    return result


def proc_alive(process):
    """Check if process is alive. Return True or False."""
    return process.poll() is None if process else False
