# coding=utf-8
import os
import sys
sys.path.insert(0, '../')

log_file = os.path.join(os.path.split(__file__)[0], 'test.log')

import logging
logging.basicConfig(level=logging.DEBUG, filename=log_file)
logger = logging.getLogger(__name__)


import unittest
from lib.rs import RS, ReplicaSet
from lib.hosts import Hosts
import lib.errors as errors
import socket
import tempfile
import time
import stat
import operator


class ReplicaSetTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix='test-replica-set', suffix='host.db')
        self.hosts = Hosts()
        self.hosts.set_settings(self.db_path)
        self.repl_cfg = {'members': [{}, {}, {}, {'rsParams': {'arbiterOnly': True}}]}
        self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if len(self.repl) > 0:
            self.repl.cleanup()

    def test_len(self):
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))
        self.repl.member_del(3)
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']) - 1)
        self.repl.repl_member_add({'rsParams': {'arbiterOnly': True}})
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))

    def test_cleanup(self):
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))
        self.repl.cleanup()
        self.assertTrue(len(self.repl) == 0)


if __name__ == '__main__':
    unittest.main()
