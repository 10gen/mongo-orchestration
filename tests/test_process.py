# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
import lib.process as process
import socket
import sys
import subprocess
import os
import random
import tempfile
import time


class PortPoolTestCase(unittest.TestCase):
    def setUp(self):
        self.hostname = process.HOSTNAME
        self.pp = process.PortPool(min_port=1025, max_port=1030)
        self.pp.change_range(min_port=1025, max_port=1030)

    def tearDown(self):
        pass

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
        self.assertTrue(port > 0)

    def test_port_check(self):
        sockets = []
        ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=ports)
        ports_opened = self.pp._PortPool__ports.copy()
        test_port = ports_opened.pop()
        self.assertTrue(test_port in self.pp._PortPool__ports)
        for port in ports:
            if port != test_port:
                sockets.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                sockets[-1].bind((self.hostname, port))
                sockets[-1].listen(0)

        self.assertTrue(test_port == self.pp.port(check=True))

        for s in sockets:
            s.close()

    def test_check_port(self):
        port = self.pp.port(check=True)
        self.assertTrue(self.pp._PortPool__check_port(port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(self.s.bind((process.HOSTNAME, port)), None)
        self.s.listen(0)
        self.assertFalse(self.pp._PortPool__check_port(port))

    def test_release_port(self):
        port = self.pp.port(check=True)
        self.assertTrue(port in self.pp._PortPool__closed)
        self.pp.release_port(port)
        self.assertFalse(port in self.pp._PortPool__closed)

    def test_refresh(self):
        sockets = []
        ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=ports)
        ports_opened = self.pp._PortPool__ports.copy()
        test_port = ports_opened.pop()
        self.assertTrue(test_port in self.pp._PortPool__ports)
        self.assertTrue(len(self.pp._PortPool__ports) > 1)
        for port in ports:
            if port != test_port:
                sockets.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                try:
                    sockets[-1].bind((self.hostname, port))
                    sockets[-1].listen(0)
                except (socket.error):
                    pass

        self.pp.refresh()
        self.assertTrue(len(self.pp._PortPool__ports) == 1)

        for s in sockets:
            s.close()

    def test_refresh_only_closed(self):
        ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=ports)
        closed_num = len(self.pp._PortPool__closed)
        self.pp.port(), self.pp.port()
        self.assertTrue(closed_num + 2 == len(self.pp._PortPool__closed))

        ports_opened = self.pp._PortPool__ports.copy()
        test_port = ports_opened.pop()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.hostname, test_port))
        s.listen(0)
        self.pp.refresh(only_closed=True)
        self.assertTrue(closed_num == len(self.pp._PortPool__closed))

        self.pp.refresh()
        self.assertTrue(closed_num + 1 == len(self.pp._PortPool__closed))

        s.close()

    def test_change_range(self):
        self.pp.change_range(min_port=1025, max_port=1033)
        ports = self.pp._PortPool__closed.union(self.pp._PortPool__ports)
        self.assertTrue(ports == set(range(1025, 1033 + 1)))

        random_ports = set([random.randint(1025, 2000) for i in xrange(15)])
        self.pp.change_range(port_sequence=random_ports)
        ports = self.pp._PortPool__closed.union(self.pp._PortPool__ports)
        self.assertTrue(ports == random_ports)


class ProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.hostname = process.HOSTNAME
        self.s = None
        self.executable = sys.executable
        self.pp = process.PortPool(min_port=1025, max_port=2000)

    def tearDown(self):
        self.s and self.s.close()

    def test_wait_for(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.pp.port()
        self.s.bind((self.hostname, port))
        self.s.listen(1)
        self.assertTrue(process.wait_for(port, 1))
        self.s.close()
        self.assertFalse(process.wait_for(port, 1))

    def test_mprocess(self):
        self.assertRaises(OSError, process.mprocess, 'fake_process_', '')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.pp.port()
        self.s.bind((self.hostname, port))
        self.s.listen(1)
        pid, host = process.mprocess(self.executable, '', port=port, timeout=2)
        self.assertTrue(pid > 0)
        self.assertEqual(host, self.hostname + ':' + str(port))
        try:
            self.s.shutdown(0)
        except socket.error:
            pass
        self.s.close()
        self.assertRaises(OSError, process.mprocess, self.executable, '', port, 2)

    def test_kill_mprocess(self):
        p = subprocess.Popen([self.executable])
        pid = p.pid
        self.assertTrue(process.proc_alive(pid))
        process.kill_mprocess(pid)
        self.assertFalse(process.proc_alive(pid))

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
        cfg = {'keyFile': key_file, 'logPath': log_path, 'dbpath': db_path}
        process.cleanup_mprocess(config_path, cfg)
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(key_file))
        self.assertFalse(os.path.exists(log_path))
        self.assertFalse(os.path.exists(db_path))

    def test_remove_path(self):
        fd, file_path = tempfile.mkstemp()
        self.assertTrue(os.path.exists(file_path))
        process.remove_path(file_path)
        self.assertFalse(os.path.exists(file_path))

        dir_path = tempfile.mkdtemp()
        fd, file_path = tempfile.mkstemp(dir=dir_path)
        process.remove_path(dir_path)
        self.assertFalse(os.path.exists(file_path))
        self.assertFalse(os.path.exists(dir_path))

    def test_write_config(self):
        config_path, cfg = process.write_config({'port': 27017, 'objcheck': 'true'})
        self.assertTrue('port' in cfg and 'objcheck' in cfg)
        self.assertTrue('dbpath' in cfg)
        self.assertTrue(os.path.exists(config_path))
        self.assertTrue(os.path.exists(cfg['dbpath']))
        self.assertTrue(os.path.isdir(cfg['dbpath']))
        config_data = open(config_path, 'r').read()
        self.assertTrue('port=27017' in config_data)
        self.assertTrue('objcheck=true' in config_data)
        self.assertTrue('dbpath={dbpath}'.format(dbpath=cfg['dbpath']) in config_data)
        process.cleanup_mprocess(config_path, cfg)

    def test_write_config_dbpath_not_exists(self):
        dbpath = tempfile.mkdtemp()
        os.removedirs(dbpath)
        self.assertFalse(os.path.exists(dbpath))
        config_path, cfg = process.write_config({'port': 27017, 'objcheck': 'true', 'dbpath': dbpath})
        self.assertTrue(os.path.exists(dbpath))

    def test_proc_alive(self):
        p = subprocess.Popen([self.executable])
        pid = p.pid
        self.assertTrue(process.proc_alive(pid))
        p.kill(), time.sleep(3)
        self.assertFalse(process.proc_alive(pid))


if __name__ == '__main__':
    unittest.main()
