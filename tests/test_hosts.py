#!/usr/bin/python
# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from lib.hosts import Host, Hosts
from lib.process import PortPool
import socket
import os
import tempfile
import time
import stat
import operator
import pymongo
from nose.plugins.attrib import attr


import logging
logger = logging.getLogger(__name__)
logging.basicConfig()

@attr('hosts')
@attr('test')
class HostsTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.path = tempfile.mktemp(prefix="test-storage")
        self.hosts = Hosts()
        self.hosts.set_settings(self.path, os.environ.get('MONGOBIN', ""))

    def remove_path(self, path):
        onerror = lambda func, filepath, exc_info: (os.chmod(filepath, stat.S_IWUSR), func(filepath))
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                time.sleep(2)
                onerror(os.remove, path, None)

    def tearDown(self):
        self.hosts.cleanup()
        self.hosts._storage.disconnect()
        self.remove_path(self.path)

    def test_singleton(self):
        self.assertEqual(id(self.hosts), id(Hosts()))

    def test_set_settings(self):
        self.path = tempfile.mktemp(prefix="test-set-settings-")
        self.hosts.set_settings(self.path)
        self.assertEqual(path, self.hosts.pids_file)

    def test_bool(self):
        self.assertEqual(False, bool(self.hosts))
        self.hosts.create('mongod', {}, autostart=False)
        self.assertTrue(True, bool(self.hosts))

    def test_operations(self):
        host_id = self.hosts.create('mongod', {}, autostart=False)
        self.assertTrue(len(self.hosts) == 1)
        self.assertTrue(host_id in self.hosts)
        host_id2 = 'host-id2'
        host2 = Host(os.path.join(os.environ.get('MONGOBIN', ''), 'mongod'), {})
        host2.start(30)
        host2_pid = host2.info()['procInfo']['pid']
        self.hosts[host_id2] = host2
        self.assertTrue(self.hosts[host_id2]['procInfo']['pid'] == host2_pid)
        self.assertTrue(host_id2 in self.hosts)
        for h_id in self.hosts:
            self.assertTrue(h_id in (host_id, host_id2))

        operator.delitem(self.hosts, host_id2)
        self.assertFalse(host_id2 in self.hosts)
        host2.stop()
        host2.cleanup()

    def test_cleanup(self):
        self.hosts.create('mongod', {}, autostart=False)
        self.hosts.create('mongod', {}, autostart=True)
        self.assertTrue(len(self.hosts) == 2)
        self.hosts.cleanup()
        self.assertTrue(len(self.hosts) == 0)

    def test_new_host(self):
        self.assertTrue(len(self.hosts) == 0)
        host_id = self.hosts.create('mongod', {}, autostart=False)
        info = self.hosts.info(host_id)
        self.assertTrue(len(self.hosts) == 1)
        self.assertEqual(info['procInfo']['pid'], None)
        host_id2 = self.hosts.create('mongod', {}, autostart=True)
        info = self.hosts.info(host_id2)
        self.assertTrue(info['procInfo']['pid'] > 0)

        self.assertRaises(OSError, self.hosts.create, 'fake_process_', {})

    def test_new_host_with_auth(self):
        host_id = self.hosts.create('mongod', {}, login='adminko', password='password', autostart=True)
        hostname = self.hosts.hostname(host_id)
        c = pymongo.MongoClient(hostname)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('adminko', 'password'))
        self.assertTrue(isinstance(c.admin.collection_names(), list))
        self.assertTrue(c.admin.logout() is None)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_hdel(self):
        self.assertEqual(len(self.hosts), 0)
        h_id = self.hosts.create('mongod', {}, autostart=True)
        self.assertEqual(len(self.hosts), 1)
        h_info = self.hosts.info(h_id)['procInfo']
        self.assertTrue(os.path.exists(h_info['params']['dbpath']))
        self.assertTrue(os.path.exists(h_info['optfile']))
        self.hosts.remove(h_id)
        self.assertEqual(len(self.hosts), 0)  # check length
        # check cleanup
        self.assertFalse(os.path.exists(h_info['params']['dbpath']))
        self.assertFalse(os.path.exists(h_info['optfile']))

    def test_hcommand(self):
        h_id = self.hosts.create('mongod', {}, autostart=False)
        self.assertTrue(self.hosts.command(h_id, 'start'))
        self.assertTrue(self.hosts.command(h_id, 'stop'))
        self.assertTrue(self.hosts.command(h_id, 'start'))
        self.assertTrue(self.hosts.command(h_id, 'restart'))
        self.assertRaises(ValueError, self.hosts.command, h_id, 'fake')

    def test_hinfo(self):
        h_id = self.hosts.create('mongod', {}, autostart=False)
        info = self.hosts.info(h_id)
        self.assertEqual(info['id'], h_id)
        self.assertEqual(info['procInfo']['pid'], None)
        self.assertEqual(info['statuses'], {})
        self.assertEqual(info['serverInfo'], {})

    def test_id_by_hostname(self):
        h_id = self.hosts.create('mongod', {}, autostart=True)
        h_uri = self.hosts.info(h_id)['uri']
        h2_id = self.hosts.create('mongod', {}, autostart=True)
        h2_uri = self.hosts.info(h2_id)['uri']
        self.assertTrue(self.hosts.id_by_hostname(h_uri) == h_id)
        self.assertTrue(self.hosts.id_by_hostname(h2_uri) == h2_id)

    def test_hostname(self):
        h_id = self.hosts.create('mongod', {}, autostart=True)
        h_uri = self.hosts.info(h_id)['uri']
        self.assertEqual(self.hosts.hostname(h_id), h_uri)

    def test_is_alive(self):
        h_id = self.hosts.create('mongod', {}, autostart=True)
        self.assertEqual(self.hosts.is_alive(h_id), True)
        self.hosts.command(h_id, 'stop')
        self.assertEqual(self.hosts.is_alive(h_id), False)

    def test_db_command(self):
        h_id = self.hosts.create('mongod', {}, autostart=False)
        self.assertRaises(pymongo.errors.PyMongoError, self.hosts.db_command, h_id, 'serverStatus', None, False)
        self.hosts.command(h_id, 'start', 10)
        self.assertEqual(self.hosts.db_command(h_id, 'serverStatus', arg=None, is_eval=False).get('ok', -1), 1)
        self.assertEqual(self.hosts.db_command(h_id, 'db.getName()', arg=None, is_eval=True), 'admin')

    def test_id_specified(self):
        id = 'xyzzy'
        h_id = self.hosts.create('mongod', {}, autostart=False, host_id=id)
        self.assertEqual(id, h_id)

@attr('hosts')
@attr('test')
class HostTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.host = Host(self.mongod, {})

    def tearDown(self):
        if hasattr(self, 'host'):
            self.host.stop()
            self.host.cleanup()

    def test_host(self):
        self.assertTrue(isinstance(self.host, Host))

    def test_init_path(self):
        self.host.cleanup()
        mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        log_dir = os.path.join(tempfile.gettempdir(), os.path.split(tempfile.mktemp())[-1])
        log_path = tempfile.mktemp(dir=log_dir)
        db_path = os.path.join(tempfile.gettempdir(), os.path.split(tempfile.mktemp())[-1])
        self.assertFalse(os.path.exists(log_dir))
        self.assertFalse(os.path.exists(db_path))
        self.host = Host(mongod, {'logpath': log_path, 'dbpath': db_path})
        self.assertTrue(os.path.exists(log_dir))
        self.assertTrue(os.path.exists(db_path))

    def test_mongos(self):
        self.host.cleanup()
        self.host = Host(self.mongod, {'configsvr': True})
        self.host.start(30)
        mongos = os.path.join(os.environ.get('MONGOBIN', ''), 'mongos')
        self.host2 = Host(mongos, {'configdb': self.host.info()['uri']})
        self.assertTrue(self.host2.start())
        self.assertTrue(self.host2.info()['statuses'].get('mongos', False))
        self.host2.stop()
        self.host2.cleanup()

    def test_run_command(self):
        self.host.start(30)

    def test_info(self):
        self.host.start(30)
        info = self.host.info()
        for item in ("uri", "statuses", "serverInfo", "procInfo", "orchestration"):
            self.assertTrue(item in info)

        fd_log, log_path = tempfile.mkstemp()
        os.close(fd_log)
        db_path = tempfile.mkdtemp()
        params = {'logpath': log_path, 'dbpath': db_path}
        host2 = Host(self.mongod, params)
        host2.start()
        info2 = host2.info()
        for param, value in params.items():
            self.assertTrue(info2['procInfo']['params'].get(param, value) == value)
        host2.stop()
        info = host2.info()
        self.assertEqual(len(info['serverInfo']), 0)
        self.assertEqual(len(info['statuses']), 0)
        self.assertEqual(info['orchestration'], 'hosts')
        host2.cleanup()

    def test_command(self):
        self.assertRaises(pymongo.errors.PyMongoError, self.host.run_command, 'serverStatus', None, False)
        self.host.start(30)
        self.assertEqual(self.host.run_command('serverStatus', arg=None, is_eval=False).get('ok', -1), 1)
        self.assertEqual(self.host.run_command('db.getName()', arg=None, is_eval=True), 'admin')

    def test_start(self):
        self.assertTrue(self.host.info()['procInfo']['pid'] is None)
        self.assertTrue(self.host.start(30))
        self.assertTrue(self.host.info()['procInfo']['pid'] > 0)

        fake_host = Host('fake_proc_', {})
        self.assertFalse(fake_host.start(5))
        fake_host.cleanup()

    def test_start_with_repair(self):
        self.host.cleanup()
        self.host = Host(self.mongod, {"journal": False})
        self.host.start(30)
        os.kill(self.host.pid, 9)
        self.assertTrue(self.host._is_locked)
        self.assertTrue(self.host.start(20))

    def test_stop(self):
        self.assertTrue(self.host.start(60))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        self.assertTrue(self.host.stop())
        self.assertRaises(socket.error, s.connect, (host, self.host.cfg['port']))

    def test_restart(self):
        self.assertTrue(self.host.start(30))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        s.shutdown(0)
        s.close()
        self.assertTrue(self.host.restart(30))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, self.host.cfg['port']))
        s.shutdown(0)
        s.close()

    def test_is_alive(self):
        self.host.start()
        self.assertTrue(self.host.is_alive)
        self.host.stop()
        self.assertFalse(self.host.is_alive)
        self.host.restart()
        self.assertTrue(self.host.is_alive)

    def test_cleanup(self):
        self.host.start(80)
        self.assertTrue(os.path.exists(self.host.cfg['dbpath']))
        self.assertTrue(os.path.exists(self.host.config_path))
        self.host.stop()
        self.host.cleanup()
        self.assertFalse(os.path.exists(self.host.cfg['dbpath']))
        self.assertFalse(os.path.exists(self.host.config_path))


@attr('hosts')
@attr('auth')
@attr('test')
class HostAuthTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.host = Host(self.mongod, {}, auth_key='secret', login='admin', password='admin')
        self.host.start()

    def tearDown(self):
        if hasattr(self, 'host'):
            assert self.host.stop()
            self.host.cleanup()

    def test_mongos(self):
        self.host.stop()
        self.host.cleanup()
        self.host = Host(self.mongod, {'configsvr': True}, auth_key='secret')
        self.host.start(30)
        mongos = os.path.join(os.environ.get('MONGOBIN', ''), 'mongos')
        self.host2 = Host(mongos, {'configdb': self.host.info()['uri']}, auth_key='secret', login='admin', password='admin')
        self.host2.start()

        for host in (self.host, self.host2):
            c = pymongo.MongoClient(host.host, host.port)
            self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
            self.assertTrue(c.admin.authenticate('admin', 'admin'))
            self.assertTrue(isinstance(c.admin.collection_names(), list))
            self.assertTrue(c.admin.logout() is None)
            self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

        self.host2.stop()
        self.host2.cleanup()

    def test_auth_connection(self):
        self.assertTrue(isinstance(self.host.connection.admin.collection_names(), list))
        c = pymongo.MongoClient(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        time.sleep(1)
        self.host.restart()
        c = pymongo.MongoClient(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_admin(self):
        c = pymongo.MongoClient(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        self.assertTrue(isinstance(c.admin.collection_names(), list))
        self.assertTrue(c.admin.logout() is None)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_collection(self):
        c = pymongo.MongoClient(self.host.host, self.host.port)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        db = c.test_host_auth
        db.add_user('user', 'userpass', roles=['readWrite'])
        c.admin.logout()

        self.assertTrue(db.authenticate('user', 'userpass'))
        self.assertTrue(db.foo.insert({'foo': 'bar'}, safe=True, wtimeout=1000))
        self.assertTrue(isinstance(db.foo.find_one(), dict))
        db.logout()
        self.assertRaises(pymongo.errors.OperationFailure, db.foo.find_one)

if __name__ == '__main__':
    unittest.main(verbosity=3)
    # suite = unittest.TestSuite()
    # suite.addTest(HostTestCase('test_start_with_repair'))
    # unittest.TextTestRunner(verbosity=2).run(suite)
