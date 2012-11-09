# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from lib.hosts import Host, Hosts
import socket
import os
import tempfile
import time
import stat


class HostsTestCase(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(prefix="test-storage")
        self.hosts = Hosts()
        self.hosts.set_settings(self.path)

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

    def test_new_host(self):
        host_id = self.hosts.h_new('mongod', {}, autostart=False)
        info = self.hosts.h_info(host_id)
        self.assertTrue(len(host_id) > 0)
        self.assertEqual(info['procInfo']['pid'], None)
        host_id2 = self.hosts.h_new('mongod', {}, autostart=True)
        info = self.hosts.h_info(host_id2)
        self.assertTrue(info['procInfo']['pid'] > 0)

    def test_hdel(self):
        self.assertEqual(len(self.hosts), 0)
        h_id = self.hosts.h_new('mongod', {}, autostart=True)
        self.assertEqual(len(self.hosts), 1)
        h_info = self.hosts.h_info(h_id)['procInfo']
        self.assertTrue(os.path.exists(h_info['params']['dbpath']))
        self.assertTrue(os.path.exists(h_info['optfile']))
        self.hosts.h_del(h_id)
        self.assertEqual(len(self.hosts), 0)  # check length
        # check cleanup
        self.assertFalse(os.path.exists(h_info['params']['dbpath']))
        self.assertFalse(os.path.exists(h_info['optfile']))

    def test_hcommand(self):
        h_id = self.hosts.h_new('mongod', {}, autostart=False)
        self.assertTrue(self.hosts.h_command(h_id, 'start'))
        self.assertTrue(self.hosts.h_command(h_id, 'stop'))
        self.assertTrue(self.hosts.h_command(h_id, 'start'))
        self.assertTrue(self.hosts.h_command(h_id, 'restart'))
        with self.assertRaises(ValueError):
            self.hosts.h_command(h_id, 'fake')

    def test_hinfo(self):
        h_id = self.hosts.h_new('mongod', {}, autostart=False)
        info = self.hosts.h_info(h_id)
        self.assertEqual(info['id'], h_id)
        self.assertEqual(info['procInfo']['pid'], None)
        self.assertEqual(info['statuses'], {})
        self.assertEqual(info['serverInfo'], {})

    def test_hosts(self):
        self.assertEqual(len(self.hosts), 0)
        h_id = self.hosts.h_new('mongod', {}, autostart=False)
        self.assertEqual(len(self.hosts), 1)
        h2_id = self.hosts.h_new('mongod', {}, autostart=False)
        for host in self.hosts:
            self.assertTrue(host in (h_id, h2_id))
        self.assertTrue(h_id in self.hosts)
        self.assertTrue(h2_id in self.hosts)

        self.hosts.h_del(h2_id)
        self.assertEqual(len(self.hosts), 1)
        self.assertFalse(h2_id in self.hosts)


class HostTestCase(unittest.TestCase):
    def setUp(self):
        self.host = Host('mongod', {}, None)

    def tearDown(self):
        if hasattr(self, 'host'):
            self.host.stop()
            self.host.cleanup()

    def test_host(self):
        self.assertTrue(isinstance(self.host, Host))

    def test_start(self):
        self.assertTrue(self.host.start(60))

    def test_stop(self):
        self.assertTrue(self.host.start(60))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        self.host.stop()
        with self.assertRaises(socket.error):
            s.connect((host, self.host.cfg['port']))

    def test_restart(self):
        self.assertTrue(self.host.start(60))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.host.hostname.split(':')[0]
        s.connect((host, self.host.cfg['port']))
        s.shutdown(0)
        s.close()
        self.assertTrue(self.host.restart(80))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, self.host.cfg['port']))
        s.shutdown(0)
        s.close()

    def test_cleanup(self):
        self.host.start(80)
        self.assertTrue(os.path.exists(self.host.cfg['dbpath']))
        self.assertTrue(os.path.exists(self.host.config_path))
        self.host.stop()
        self.host.cleanup()
        self.assertFalse(os.path.exists(self.host.cfg['dbpath']))
        self.assertFalse(os.path.exists(self.host.config_path))

    def test_info(self):
        self.host.start(80)
        info = self.host.info()
        for item in ("uri", "statuses", "serverInfo", "procInfo"):
            self.assertTrue(item in info)


if __name__ == '__main__':
    unittest.main()
