# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
import modules.process as process
import socket
import sys
import subprocess
import os


class ProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.hostname = process.HOSTNAME
        self.s = None
        self.executable = sys.executable
        self.pp = process.PortPool(min_port=1025, max_port=2000)

    def tearDown(self):
        self.s and self.s.close()

    def test_find_open_port_success(self):
        port = self.pp.port()
        self.assertGreater(port, 0)

    def test_find_open_port_check_socket(self):
        port = self.pp.port()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(self.s.bind((process.HOSTNAME, port)), None)

    def test_find_open_port_fail(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.pp.port()
        self.s.bind((self.hostname, port))
        self.assertRaises(Exception, self.pp.port(), (4547, 4547))
        self.assertRaises(Exception, self.pp.port(), (546, 7))

    def test_wait_for(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.pp.port()
        self.s.bind((self.hostname, port))
        self.s.listen(1)
        self.assertTrue(process.wait_for(port, 1))
        # self.s.shutdown(0)
        self.s.close()
        self.assertFalse(process.wait_for(port, 1))

    def test_mprocess(self):
        with self.assertRaises(OSError):
            process.mprocess('fake-process_', '', None)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = self.pp.port()
        self.s.bind((self.hostname, port))
        self.s.listen(1)
        pid, host = process.mprocess(self.executable, '', port=port, timeout=2)
        self.assertGreater(pid, 0)
        self.assertEqual(host, self.hostname + ':' + str(port))
        try:
            self.s.shutdown(0)
        except socket.error:
            pass
        self.s.close()
        with self.assertRaises(OSError):
            process.mprocess(self.executable, '', port=port, timeout=2)

    def test_kill_mprocess(self):
        p = subprocess.Popen([self.executable])
        pid = p.pid
        process.kill_mprocess(pid)
        self.assertFalse(process.proc_alive(pid))

    def test_port_pool(self):
        pp = process.PortPool()
        len1 = len(pp._PortPool__ports)
        port = pp.port()
        self.assertEqual(len1 - 1, len(pp._PortPool__ports))
        pp.release_port(port)
        self.assertEqual(len1, len(pp._PortPool__ports))
        len1 = len(pp._PortPool__ports)
        pp.port(), pp.port(), pp.port()
        self.assertEqual(len1 - 3, len(pp._PortPool__ports))
        pp.refresh()
        self.assertGreater(len(pp._PortPool__ports), len1)
        ports = [pp.port() for i in xrange(12)]
        pp.change_range(port_sequence=ports)
        self.assertEqual(len(ports), len(pp._PortPool__ports))
        for i in xrange(0, len(ports)):
            self.assertTrue(pp.port() in ports)
        self.assertEqual(len(pp._PortPool__ports), 0)
        pp.port()
        self.assertEqual(len(ports) - 1, len(pp._PortPool__ports))

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

    def test_cleanup(self):
        config_path, cfg = process.write_config({'port': 27017, 'objcheck': 'true'}, auth_key="secret")
        for key in ('dbpath', 'keyFile'):
            self.assertTrue(os.path.exists(cfg[key]))
        process.cleanup_mprocess(config_path, cfg)
        for key in ('dbpath', 'keyFile'):
            self.assertFalse(os.path.exists(cfg[key]))


if __name__ == '__main__':
    unittest.main()
