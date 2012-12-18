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
        path = tempfile.mktemp(prefix="test-set-settings-")
        self.hosts.set_settings(path)
        self.assertEqual(path, self.hosts.pids_file)
        self.remove_path(path)

    def test_bool(self):
        self.assertEqual(False, bool(self.hosts))
        self.hosts.create('mongod', {}, autostart=False)
        self.assertTrue(True, bool(self.hosts))

    def test_operations(self):
        host_id = self.hosts.create('mongod', {}, autostart=False)
        self.assertTrue(len(self.hosts) == 1)
        self.assertTrue(host_id in self.hosts)
        host_id2, host2 = 'host-id2', Host('mongod', {}, None)
        host2.start(20)
        host2_pid = host2.info()['procInfo']['pid']
        self.hosts[host_id2] = host2
        self.assertTrue(self.hosts[host_id2]['procInfo']['pid'] == host2_pid)
        self.assertTrue(host_id2 in self.hosts)
        for h_id in self.hosts:
            self.assertTrue(h_id in (host_id, host_id2))

        operator.delitem(self.hosts, host_id2)
        self.assertFalse(host_id2 in self.hosts)
        host2.stop(), host2.cleanup()

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
        host_id = self.hosts.create('mongod', {}, login='adminko', password='XXX', autostart=True)
        hostname = self.hosts.hostname(host_id)
        c = pymongo.Connection(hostname)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('adminko', 'XXX'))
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


class HostTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.host = Host(mongod, {}, None)

    def tearDown(self):
        if hasattr(self, 'host'):
            self.host.stop()
            self.host.cleanup()

    def test_host(self):
        self.assertTrue(isinstance(self.host, Host))

    def test_info(self):
        self.host.start(10)
        info = self.host.info()
        for item in ("uri", "statuses", "serverInfo", "procInfo"):
            self.assertTrue(item in info)

        fd_log, log_path = tempfile.mkstemp()
        db_path = tempfile.mkdtemp()
        params = {'logPath': log_path, 'dbpath': db_path}
        host2 = Host('mongod', params, None)
        host2.start(10)
        info2 = host2.info()
        for param, value in params.items():
            self.assertTrue(info2['procInfo']['params'].get(param, value) == value)
        host2.stop()
        host2.cleanup()

    def test_start(self):
        self.assertTrue(self.host.info()['procInfo']['pid'] is None)
        self.assertTrue(self.host.start(10))
        self.assertTrue(self.host.info()['procInfo']['pid'] > 0)

        fake_host = Host('fake_proc_', {}, None)
        self.assertFalse(fake_host.start(5))
        fake_host.cleanup()

    def test_stop(self):
        self.assertTrue(self.host.start(60))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        self.assertTrue(self.host.stop())
        self.assertRaises(socket.error, s.connect, (host, self.host.cfg['port']))

    def test_restart(self):
        self.assertTrue(self.host.start(20))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        s.shutdown(0)
        s.close()
        self.assertTrue(self.host.restart(20))
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


class HostAuthTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.host = Host(mongod, {}, None, login='admin', password='admin')
        self.host.start()

    def tearDown(self):
        if hasattr(self, 'host'):
            self.host.stop()
            self.host.cleanup()
        pass

    def test_auth_connection(self):
        self.assertTrue(isinstance(self.host.connection.admin.collection_names(), list))
        c = pymongo.Connection(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.host.restart()
        c = pymongo.Connection(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_admin(self):
        c = pymongo.Connection(self.host.host, self.host.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        self.assertTrue(isinstance(c.admin.collection_names(), list))
        self.assertTrue(c.admin.logout() is None)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_collection(self):
        c = pymongo.Connection(self.host.host, self.host.port)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        db = c.test_host_auth
        db.add_user('user', 'userpass')
        c.admin.logout()

        self.assertTrue(db.authenticate('user', 'userpass'))
        self.assertTrue(db.foo.insert({'foo': 'bar'}, safe=True, wtimeout=1000))
        self.assertTrue(isinstance(db.foo.find_one(), dict))
        db.logout()
        self.assertRaises(pymongo.errors.OperationFailure, db.foo.find_one)

if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(HostsTestCase('test_new_host_with_auth'))
    suite.addTest(HostsTestCase('test_is_alive'))
    suite.addTest(HostTestCase('test_is_alive'))
    suite.addTest(HostAuthTestCase('test_auth_connection'))
    suite.addTest(HostAuthTestCase('test_auth_admin'))
    suite.addTest(HostAuthTestCase('test_auth_collection'))
    unittest.TextTestRunner(verbosity=2).run(suite)
