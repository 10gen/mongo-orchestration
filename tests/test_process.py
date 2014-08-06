#!/usr/bin/python
# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
import lib.process as process
import socket
import sys
import subprocess
import os
import platform
import random
import tempfile
import time

from unittest.case import SkipTest
from nose.plugins.attrib import attr


@attr('process')
@attr('portpool')
@attr('test')
class PortPoolTestCase(unittest.TestCase):

    def setUp(self):
        self.hostname = process.HOSTNAME
        self.pp = process.PortPool()
        self.pp.change_range(min_port=1025, max_port=1080)
        self.sockets = {}

    def tearDown(self):
        for s in self.sockets:
            self.sockets[s].close()

    def listen_port(self, port, max_connection=0):
        if self.sockets.get(port, None):
            self.sockets[port].close()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((process.HOSTNAME, port))
        s.listen(max_connection)
        self.sockets[port] = s

    def test_singleton(self):
        pp2 = process.PortPool(min_port=1025, max_port=1038)
        self.failUnlessEqual(id(self.pp), id(pp2))

    def test_port_sequence(self):
        ports = set([1025, 1026, 1027, 1028, 30, 28, 22, 45])
        self.pp.change_range(port_sequence=ports)
        _ports = self.pp._PortPool__closed.union(self.pp._PortPool__ports)
        self.assertEqual(ports, _ports)

    def test_find_port(self):
        port = self.pp.port()
        self.pp.change_range(port, port)
        port = self.pp.port()
        self.assertTrue(port > 0)
        self.listen_port(port)
        self.assertRaises(IndexError, self.pp.port)

    def test_port_with_check(self):
        self.pp.change_range(min_port=1100, max_port=1200)
        port1, port2 = self.pp.port(check=True), self.pp.port(check=True)
        self.pp.change_range(port_sequence=[port1, port2])
        self.listen_port(port1, 0)
        self.assertTrue(port2 == self.pp.port(check=True))

    def test_check_port(self):
        port = self.pp.port(check=True)
        self.assertTrue(self.pp._PortPool__check_port(port))
        self.listen_port(port)
        self.assertFalse(self.pp._PortPool__check_port(port))

    def test_release_port(self):
        port = self.pp.port(check=True)
        self.assertTrue(port in self.pp._PortPool__closed)
        self.pp.release_port(port)
        self.assertFalse(port in self.pp._PortPool__closed)

    def test_refresh(self):
        ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=ports)
        ports_opened = self.pp._PortPool__ports.copy()
        test_port = ports_opened.pop()
        self.assertTrue(test_port in self.pp._PortPool__ports)
        self.assertTrue(len(self.pp._PortPool__ports) > 1)
        for port in ports:
            if port != test_port:
                try:
                    self.listen_port(port)
                except (socket.error):
                    pass

        self.pp.refresh()
        self.assertTrue(len(self.pp._PortPool__ports) == 1)

    def test_refresh_only_closed(self):
        ports = set([random.randint(1025, 2000) for _ in xrange(15)])
        self.pp.change_range(port_sequence=ports)
        closed_num = len(self.pp._PortPool__closed)
        self.pp.port(), self.pp.port()
        self.assertTrue(closed_num + 2 == len(self.pp._PortPool__closed))

        ports_opened = self.pp._PortPool__ports.copy()
        test_port = ports_opened.pop()
        self.listen_port(test_port)
        self.pp.refresh(only_closed=True)
        self.assertTrue(closed_num == len(self.pp._PortPool__closed))

        self.pp.refresh()
        self.assertTrue(closed_num + 1 == len(self.pp._PortPool__closed))

    def test_change_range(self):
        self.pp.change_range(min_port=1025, max_port=1033)
        ports = self.pp._PortPool__closed.union(self.pp._PortPool__ports)
        self.assertTrue(ports == set(range(1025, 1033 + 1)))

        random_ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=random_ports)
        ports = self.pp._PortPool__closed.union(self.pp._PortPool__ports)
        self.assertTrue(ports == random_ports)


@attr('process')
@attr('test')
class ProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.hostname = process.HOSTNAME
        self.s = None
        self.executable = sys.executable
        self.pp = process.PortPool(min_port=1025, max_port=2000)
        self.sockets = {}
        self.tmp_files = list()
        self.bin_path = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.db_path = tempfile.mkdtemp()
        self.cfg = {"noprealloc": True, "smallfiles": True, "oplogSize": 10, 'dbpath': self.db_path}

    def tearDown(self):
        for s in self.sockets:
            self.sockets[s].close()
        if self.cfg:
            process.cleanup_mprocess('', self.cfg)
        for item in self.tmp_files:
            if os.path.exists(item):
                os.remove(item)

    def listen_port(self, port, max_connection=0):
        if self.sockets.get(port, None):
            self.sockets[port].close()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((process.HOSTNAME, port))
        s.listen(max_connection)
        self.sockets[port] = s

    def test_wait_for(self):
        port = self.pp.port(check=True)
        self.listen_port(port, max_connection=1)
        self.assertTrue(process.wait_for(port, 1))
        self.sockets.pop(port).close()
        self.assertFalse(process.wait_for(port, 1))

    def test_repair(self):
        port = self.pp.port(check=True)
        # Assume we're testing on 64-bit machines.
        self.cfg['nojournal'] = True
        lock_file = os.path.join(self.cfg['dbpath'], 'mongod.lock')
        config_path = process.write_config(self.cfg)
        self.tmp_files.append(config_path)
        proc, host = process.mprocess(self.bin_path, config_path, port=port, timeout=60)
        self.assertTrue(os.path.exists(lock_file))
        if platform.system() == 'Windows':
            # mongod.lock cannot be read by any external process on Windows.
            with self.assertRaises(IOError):
                open(lock_file, 'r')
        else:
            self.assertTrue(len(open(lock_file, 'r').read()) > 0)
        proc.terminate()
        process.repair_mongo(self.bin_path, self.cfg['dbpath'])
        self.assertFalse(len(open(lock_file, 'r').read()) > 0, "lock_file contains: {0}".format(open(lock_file, 'r').read()))

    def test_mprocess_fail(self):
        fd_cfg, config_path = tempfile.mkstemp()
        os.close(fd_cfg)
        self.tmp_files.append(config_path)
        self.assertRaises(OSError, process.mprocess, 'fake-process_', config_path, None, 30)
        process.write_config({"fake": True}, config_path)
        self.assertRaises(OSError, process.mprocess, 'mongod', config_path, None, 30)

    def test_mprocess(self):
        port = self.pp.port(check=True)
        config_path = process.write_config(self.cfg)
        self.tmp_files.append(config_path)
        result = process.mprocess(self.bin_path, config_path, port=port, timeout=60)
        self.assertTrue(isinstance(result, tuple))
        proc, host = result
        self.assertTrue(isinstance(proc, subprocess.Popen))
        self.assertTrue(isinstance(host, str))
        process.kill_mprocess(proc)

    def test_mprocess_timeout(self):
        port = self.pp.port()
        cfg = self.cfg.copy()
        cfg.pop('noprealloc')
        cfg.pop('smallfiles')
        cfg['journal'] = True
        config_path = process.write_config(cfg)
        self.tmp_files.append(config_path)
        proc, host = process.mprocess(self.bin_path, config_path, port, 0)
        self.assertTrue(isinstance(proc, subprocess.Popen))
        self.assertTrue(isinstance(host, str))
        process.kill_mprocess(proc)
        if platform.system() == 'Windows':
            raise SkipTest("Cannot test mongod startup timeout on Windows.")
        with self.assertRaises(OSError):
            result = process.mprocess(self.bin_path, config_path, port, 0.1)
            print(result)

    def test_mprocess_busy_port(self):
        config_path = process.write_config(self.cfg)
        self.tmp_files.append(config_path)
        port = self.pp.port()
        self.listen_port(port, max_connection=0)
        pid, host = process.mprocess(self.executable, config_path, port=port, timeout=2)
        self.assertTrue(pid > 0)
        self.assertEqual(host, self.hostname + ':' + str(port))
        self.sockets.pop(port).close()
        self.assertRaises(OSError, process.mprocess, self.executable, '', port, 1)

    def test_kill_mprocess(self):
        p = subprocess.Popen([self.executable])
        self.assertTrue(process.proc_alive(p))
        process.kill_mprocess(p)
        self.assertFalse(process.proc_alive(p))

    def test_cleanup_process(self):
        fd_cfg, config_path = tempfile.mkstemp()
        fd_key, key_file = tempfile.mkstemp()
        fd_log, log_path = tempfile.mkstemp()
        db_path = tempfile.mkdtemp()
        self.assertTrue(os.path.exists(config_path))
        self.assertTrue(os.path.exists(key_file))
        self.assertTrue(os.path.exists(log_path))
        self.assertTrue(os.path.exists(db_path))
        os.fdopen(fd_cfg, 'w').write("keyFile={key_file}\nlogPath={log_path}\ndbpath={db_path}".format(**locals()))
        for fd in (fd_cfg, fd_key, fd_log):
            try:
                os.close(fd)
            except OSError:
                # fd_cfg may be closed already if fdopen() didn't raise
                pass
        cfg = {'keyFile': key_file, 'logPath': log_path, 'dbpath': db_path}
        process.cleanup_mprocess(config_path, cfg)
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(key_file))
        self.assertFalse(os.path.exists(log_path))
        self.assertFalse(os.path.exists(db_path))

    def test_remove_path(self):
        fd, file_path = tempfile.mkstemp()
        os.close(fd)
        self.assertTrue(os.path.exists(file_path))
        process.remove_path(file_path)
        self.assertFalse(os.path.exists(file_path))

        dir_path = tempfile.mkdtemp()
        fd, file_path = tempfile.mkstemp(dir=dir_path)
        os.close(fd)
        process.remove_path(dir_path)
        self.assertFalse(os.path.exists(file_path))
        self.assertFalse(os.path.exists(dir_path))

    def test_write_config(self):
        cfg = {'port': 27017, 'objcheck': 'true'}
        config_path = process.write_config(cfg)
        self.assertTrue(os.path.exists(config_path))
        config_data = open(config_path, 'r').read()
        self.assertTrue('port=27017' in config_data)
        self.assertTrue('objcheck=true' in config_data)
        process.cleanup_mprocess(config_path, cfg)

    def test_write_config_with_specify_config_path(self):
        cfg = {'port': 27017, 'objcheck': 'true'}
        fd_key, file_path = tempfile.mkstemp()
        os.close(fd_key)
        config_path = process.write_config(cfg, file_path)
        self.assertEqual(file_path, config_path)
        process.cleanup_mprocess(config_path, cfg)

    def test_proc_alive(self):
        p = subprocess.Popen([self.executable])
        self.assertTrue(process.proc_alive(p))
        p.terminate()
        p.wait()
        self.assertFalse(process.proc_alive(p))
        self.assertFalse(process.proc_alive(None))

    def test_read_config(self):
        cfg = {"noprealloc": True, "smallfiles": False, "oplogSize": 10, "other": "some string"}
        config_path = process.write_config(cfg)
        self.tmp_files.append(config_path)
        self.assertEqual(process.read_config(config_path), cfg)


if __name__ == '__main__':
    unittest.main(verbosity=3)
    # suite = unittest.TestSuite()
    # suite.addTest(ProcessTestCase('test_repair'))
    # unittest.TextTestRunner(verbosity=2).run(suite)
