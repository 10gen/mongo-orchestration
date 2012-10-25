# coding=utf-8
import process
from uuid import uuid4
from singleton import Singleton
from storage import Storage
import pymongo


class Hosts(Singleton):
    """ Hosts is a dict-like collection for Host objects"""
    _storage = None

    def set_settings(self, pids_file):
        """set path to storage"""
        self._storage = Storage(pids_file, 'hosts')
        self.pids_file = pids_file
        self.cleanup()

    def __getitem__(self, key):
        return self.h_info(key)

    def __setitem__(self, key, value):
        if isinstance(value, Host):
            self._storage[key] = value
        else:
            raise ValueError

    def __delitem__(self, key):
        host = self._storage.popitem(key)
        del(host)

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
        for host_id in self._storage:
            self.h_del(host_id)

    def h_new(self, name, params, auth_key=None, timeout=300, autostart=True):
        """create new host
        Args:
           name - process name or path
           params - dictionary with specific params for instance
           auth_key - authorization key
           timeout -  specify how long, in seconds, a command can take before times out.
           autostart - (default: True), autostart instance
        Return host_id
           where host_id - id which can use to take the host from hosts collection
        """
        try:
            host_id, host = str(uuid4()), Host(name, params, auth_key)
            if autostart:
                if not host.start(timeout):
                    raise OSError
            self[host_id] = host
            return host_id
        except:
            raise

    def h_del(self, host_id):
        """remove host and data stuff
        Args:
            host_id - host identity
        """
        host = self._storage.pop(host_id)
        host.stop()
        host.cleanup()

    def h_command(self, host_id, command, *args):
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

    def h_info(self, host_id):
        """return dicionary object with info about host
        Args:
            host_id - host identity
        """
        result = self._storage[host_id].info()
        result['id'] = host_id
        return result

    def h_id_by_hostname(self, hostname):
        for host_id in self._storage:
            if self._storage[host_id].hostname == hostname:
                return host_id


class Host(object):
    """Class Host represents behaviour of  mongo instances """

    # default params for all mongo instances
    default_params = {"noprealloc": True, "nojournal": True, "smallfiles": True, "oplogSize": 10}

    def __init__(self, name, params, auth_key):
        """Args:
            name - name of process (mongod or mongos)
            params - dictionary with params for mongo process
            auth_key - authorization key
        """
        for key in self.default_params:
            if key not in params:
                params[key] = self.default_params[key]

        self.config_path, self.cfg = process.write_config(params, auth_key)
        self.pid = None  # process pid
        self.host = None  # hostname without port
        self.port = self.cfg.get('port', None)  # connection port
        self.hostname = None  # string like host:port
        self.name = name  # name of process

    def info(self):
        """return info about host as dict object"""
        proc_info = {"name": self.name, "params": self.cfg, "alive": process.proc_alive(self.pid),
                     "pid": self.pid, "optfile": self.config_path}

        server_info = {}
        status_info = {}
        if self.hostname and self.cfg.get('port', None):
            try:
                c = pymongo.Connection(self.hostname.split(':')[0], self.cfg['port'])
                server_info = c.server_info()
                status_info = {"primary": c.is_primary, "mongos": c.is_mongos, "locked": c.is_locked}
            except pymongo.errors.AutoReconnect:
                pass

        return {"uri": self.hostname, "statuses": status_info, "serverInfo": server_info, "procInfo": proc_info}

    def start(self, timeout=300):
        """start host
        return True of False"""
        try:
            self.pid, self.hostname = process.mprocess(self.name, self.config_path, self.cfg['port'], timeout)
            self.host = self.hostname.split(':')[0]
            self.port = int(self.hostname.split(':')[1])
        except OSError:
            return False
        return True

    def stop(self):
        """stop host"""
        process.kill_mprocess(self.pid)

    def restart(self, timeout=300):
        """restart host: stop() and start()
        return status of start command
        """
        self.stop()
        return self.start(timeout)

    def cleanup(self):
        """remove host data"""
        process.cleanup_mprocess(self.config_path, self.cfg)
