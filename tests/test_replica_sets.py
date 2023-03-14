#!/usr/bin/python
# coding=utf-8
# Copyright 2012-2023 MongoDB, Inc.
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

import logging
import sys
import operator
import time

import pymongo

sys.path.insert(0, '../')

from mongo_orchestration.common import (
    connected)
from mongo_orchestration.replica_sets import ReplicaSet, ReplicaSets
from mongo_orchestration.servers import Servers
from mongo_orchestration.process import PortPool
from tests import (
    SkipTest, unittest, assert_eventually,
    HOSTNAME)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReplicaSetsTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.rs = ReplicaSets()

    def tearDown(self):
        self.rs.cleanup()

    def waiting(self, fn, timeout=300, sleep=10):
        t_start = time.time()
        while not fn():
            if time.time() - t_start > timeout:
                return False
            time.sleep(sleep)
        return True

    def test_singleton(self):
        self.assertEqual(id(self.rs), id(ReplicaSets()))

    def test_bool(self):
        self.assertEqual(False, bool(self.rs))
        self.rs.create({'id': 'test-rs-1', 'members': [{}, {}]})
        self.assertEqual(True, bool(self.rs))

    def test_operations(self):
        repl_cfg = {'members': [{}, {}]}
        repl = ReplicaSet(repl_cfg)

        self.assertEqual(len(self.rs), 0)
        operator.setitem(self.rs, 1, repl)
        self.assertEqual(len(self.rs), 1)
        self.assertEqual(operator.getitem(self.rs, 1).repl_id, repl.repl_id)
        operator.delitem(self.rs, 1)
        self.assertEqual(len(self.rs), 0)
        self.assertRaises(KeyError, operator.getitem, self.rs, 1)

    def test_operations2(self):
        self.assertTrue(len(self.rs) == 0)
        self.rs.create({'id': 'test-rs-1', 'members': [{}, {}]})
        self.rs.create({'id': 'test-rs-2', 'members': [{}, {}]})
        self.assertTrue(len(self.rs) == 2)
        for key in self.rs:
            self.assertTrue(key in ('test-rs-1', 'test-rs-2'))
        for key in ('test-rs-1', 'test-rs-2'):
            self.assertTrue(key in self.rs)

    def test_cleanup(self):
        self.assertTrue(len(self.rs) == 0)
        self.rs.create({'id': 'test-rs-1', 'members': [{}, {}]})
        self.rs.create({'id': 'test-rs-2', 'members': [{}, {}]})
        self.assertTrue(len(self.rs) == 2)
        self.rs.cleanup()
        self.assertTrue(len(self.rs) == 0)

    def test_rs_new(self):
        port1, port2 = PortPool().port(check=True), PortPool().port(check=True)
        repl_id = self.rs.create({'id': 'test-rs-1',
                                  'members': [{"procParams": {"port": port1}},
                                              {"procParams": {"port": port2}}
                                              ]})
        return
        self.assertEqual(repl_id, 'test-rs-1')
        server1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        server2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        c = pymongo.MongoClient([server1, server2], replicaSet=repl_id)
        self.assertEqual(c.admin.command("replSetGetConfig")['config']['_id'], repl_id)
        c.close()

    def test_rs_new_with_auth(self):
        port1, port2 = PortPool().port(check=True), PortPool().port(check=True)
        repl_id = self.rs.create({'id': 'test-rs-1',
                                  'auth_key': 'sercret', 'login': 'admin', 'password': 'admin',
                                  'members': [{"procParams": {"port": port1}},
                                              {"procParams": {"port": port2}}
                                              ]})
        self.assertEqual(repl_id, 'test-rs-1')
        server1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        server2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        c = pymongo.MongoClient([server1, server2], replicaSet=repl_id)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)
        c.close()
        c = pymongo.MongoClient([server1, server2], replicaSet=repl_id, username='admin', password='admin')
        self.assertTrue(isinstance(c.admin.list_collection_names(), list))
        c.close()

    def test_info(self):
        repl_id = self.rs.create({'id': 'test-rs-1', 'members': [{}, {}]})
        info = self.rs.info(repl_id)
        self.assertTrue(isinstance(info, dict))
        for item in ("id", "mongodb_uri", "members", "orchestration"):
            self.assertTrue(item in info)

        self.assertEqual(info['id'], repl_id)
        self.assertEqual(len(info['members']), 2)
        mongodb_uri = info['mongodb_uri']
        for member in self.rs.members(repl_id):
            self.assertIn(member['host'], mongodb_uri)
        self.assertTrue(mongodb_uri.find('mongodb://') == 0)
        self.assertEqual(info['orchestration'], 'replica_sets')

    def test_info_with_auth(self):
        repl_id = self.rs.create({'id': 'test-rs-1', 'login': 'admin', 'password': 'admin', 'members': [{}, {}]})
        info = self.rs.info(repl_id)
        self.assertTrue(isinstance(info, dict))
        self.assertEqual(info['id'], repl_id)
        self.assertEqual(len(info['members']), 2)

    def test_primary(self):
        repl_id = self.rs.create({'id': 'test-rs-1', 'members': [{}, {}]})
        primary = self.rs.primary(repl_id)['mongodb_uri']
        c = connected(pymongo.MongoClient(primary))
        self.assertTrue(c.is_primary)
        c.close()

    def test_primary_stepdown(self):
        # This tests Server,
        # but only makes sense in the context of a replica set.
        repl_id = self.rs.create(
            {'id': 'test-rs-stepdown', 'members': [{}, {}, {}]})
        primary = self.rs.primary(repl_id)
        primary_server = Servers()._storage[primary['server_id']]
        time.sleep(20)

        # No Exception.
        primary_server.stepdown()
        self.assertNotEqual(primary['mongodb_uri'],
                            self.rs.primary(repl_id)['mongodb_uri'])

    def test_rs_del(self):
        self.rs.create({'members': [{}, {}]})
        repl_id = self.rs.create({'members': [{}, {}]})
        self.assertEqual(len(self.rs), 2)
        primary = self.rs.primary(repl_id)['mongodb_uri']
        connected(pymongo.MongoClient(primary))  # No error.
        self.rs.remove(repl_id)
        self.assertEqual(len(self.rs), 1)
        with self.assertRaises(pymongo.errors.PyMongoError):
            connected(pymongo.MongoClient(primary))

    def test_members(self):
        port1, port2 = PortPool().port(check=True), PortPool().port(check=True)
        server1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        server2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        repl_id = self.rs.create({'members': [{"procParams": {"port": port1}}, {"procParams": {"port": port2}}]})
        members = self.rs.members(repl_id)
        self.assertEqual(len(members), 2)
        self.assertTrue(server1 in [member['host'] for member in members])
        self.assertTrue(server2 in [member['host'] for member in members])

    def test_secondaries(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}, {}]})
        secondaries = self.rs.secondaries(repl_id)
        self.assertEqual(len(secondaries), 2)

    def test_arbiters(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}, {"rsParams": {"arbiterOnly": True}}]})
        arbiters = self.rs.arbiters(repl_id)
        self.assertEqual(len(arbiters), 1)

    def test_hidden(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}, {"rsParams": {"priority": 0, "hidden": True}}]})
        hidden = self.rs.hidden(repl_id)
        self.assertEqual(len(hidden), 1)

    def test_passives(self):
        raise SkipTest("test is not currently working")
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'secondaryDelaySecs': 5}}]}
        repl_id = self.rs.create(config)
        passives = self.rs.passives(repl_id)
        self.assertEqual(len(passives), 1)

    def test_servers(self):
        raise SkipTest("test is not currently working")
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'secondaryDelaySecs': 5}}]}
        repl_id = self.rs.create(config)
        servers = self.rs.servers(repl_id)
        self.assertEqual(len(servers), 1)

    def test_compare_passives_and_servers(self):
        raise SkipTest("test is not currently working")
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'secondaryDelaySecs': 5}}]}

        repl_id = self.rs.create(config)
        passives = [server['host'] for server in self.rs.passives(repl_id)]
        servers = [server['host'] for server in self.rs.servers(repl_id)]
        for item in passives:
            self.assertTrue(item not in servers)

        for item in servers:
            self.assertTrue(item not in passives)

    def test_member_info(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {"rsParams": {"arbiterOnly": True}}, {"rsParams": {"priority": 0, "hidden": True}}]})
        info = self.rs.member_info(repl_id, 0)
        for key in ('procInfo', 'mongodb_uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 0)
        self.assertTrue(info['statuses']['primary'])

        info = self.rs.member_info(repl_id, 1)
        for key in ('procInfo', 'mongodb_uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 1)
        self.assertTrue(info['rsInfo']['arbiterOnly'])

        info = self.rs.member_info(repl_id, 2)
        for key in ('procInfo', 'mongodb_uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 2)
        self.assertTrue(info['rsInfo']['hidden'])

    def test_tagging(self):
        tags_0 = {"status": "primary"}
        tags_1 = {"status": "arbiter"}
        tags_2 = {"status": "hidden"}
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5, "tags": tags_0}}, {"rsParams": {"arbiterOnly": True}, "tags": tags_1}, {"rsParams": {"priority": 0, "hidden": True, "tags": tags_2}}]})
        self.assertEqual(tags_0, self.rs.primary(repl_id)['rsInfo']['tags'])

        member_arbiter = self.rs.arbiters(repl_id)[0]['_id']
        self.assertFalse('tags' in self.rs.member_info(repl_id, member_arbiter)['rsInfo'])

        member_hidden = self.rs.hidden(repl_id)[0]['_id']
        self.assertTrue('tags' in self.rs.member_info(repl_id, member_hidden)['rsInfo'])

    def test_member_del(self):
        repl_id = self.rs.create(
            {'members': [{"rsParams": {"priority": 1.5}}, {}, {}]})
        self.assertEqual(len(self.rs.members(repl_id)), 3)
        assert_eventually(lambda: len(self.rs.secondaries(repl_id)) > 0)
        secondary = self.rs.secondaries(repl_id)[0]
        connected(pymongo.MongoClient(secondary['host']))  # No error.
        self.assertTrue(self.rs.member_del(repl_id, secondary['_id']))
        self.assertEqual(len(self.rs.members(repl_id)), 2)
        with self.assertRaises(pymongo.errors.PyMongoError):
            connected(pymongo.MongoClient(secondary['host']))

    def test_member_add(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}]})
        self.assertEqual(len(self.rs.members(repl_id)), 2)
        member_id = self.rs.member_add(repl_id, {"rsParams": {"priority": 0, "hidden": True}})
        self.assertEqual(len(self.rs.members(repl_id)), 3)
        info = self.rs.member_info(repl_id, member_id)
        self.assertTrue(info['rsInfo']['hidden'])

    def test_member_command(self):
        _id = 1
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}]})
        self.assertTrue(self.rs.member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.member_command(repl_id, _id, 'stop')
        self.assertFalse(self.rs.member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.member_command(repl_id, _id, 'start')
        self.assertTrue(self.rs.member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.member_command(repl_id, _id, 'restart')
        self.assertTrue(self.rs.member_info(repl_id, _id)['procInfo']['alive'])

    def test_member_freeze(self):
        # This tests Server, but only makes sense in the context of a replica set.
        repl_id = self.rs.create(
            {'members': [{"rsParams": {"priority": 19}},
                         {"rsParams": {"priority": 5}}, {}]})
        next_primary_info = self.rs.member_info(repl_id, 2)
        next_primary = next_primary_info['mongodb_uri']
        secondary_info = self.rs.member_info(repl_id, 1)
        secondary_server = Servers()._storage[secondary_info['server_id']]
        primary_info = self.rs.member_info(repl_id, 0)
        primary_server = Servers()._storage[primary_info['server_id']]

        assert_eventually(lambda: primary_server.connection.is_primary)

        def freeze_and_stop():
            self.assertTrue(secondary_server.freeze(100))
            try:
                # Call replSetStepDown before killing the primary's process.
                # This raises OperationFailure if no secondaries are capable
                # of taking over.
                primary_server.connection.admin.command('replSetStepDown', 10)
            except pymongo.errors.AutoReconnect:
                # Have to stop the server as well so it doesn't get reelected.
                primary_server.stop()
                return True
            except pymongo.errors.OperationFailure:
                # No secondaries within 10 seconds of my optime...
                return False

        assert_eventually(freeze_and_stop, "Primary didn't step down.")
        assert_eventually(lambda: (
            self.rs.primary(repl_id)['mongodb_uri'] == next_primary),
            "Secondary did not freeze.",
            max_tries=120
        )
        assert_eventually(lambda: (
            self.rs.primary(repl_id)['mongodb_uri'] ==
            self.rs.member_info(repl_id, 1)['mongodb_uri']),
            "Higher priority secondary never promoted.",
            max_tries=120
        )

    def test_member_update(self):
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {"rsParams": {"priority": 0, "hidden": True}}, {}]})
        hidden = self.rs.hidden(repl_id)[0]
        self.assertTrue(self.rs.member_info(repl_id, hidden['_id'])['rsInfo']['hidden'])
        self.rs.member_update(repl_id, hidden['_id'], {"rsParams": {"priority": 1, "hidden": False}})
        self.assertEqual(len(self.rs.hidden(repl_id)), 0)
        self.assertFalse(self.rs.member_info(repl_id, hidden['_id'])['rsInfo'].get('hidden', False))

    def test_member_update_with_auth(self):
        repl_id = self.rs.create({'login': 'admin', 'password': 'admin',
                                 'members': [{"rsParams": {"priority": 1.5}},
                                             {"rsParams": {"priority": 0, "hidden": True}},
                                             {}]})
        hidden = self.rs.hidden(repl_id)[0]
        self.assertTrue(self.rs.member_info(repl_id, hidden['_id'])['rsInfo']['hidden'])
        self.rs.member_update(repl_id, hidden['_id'], {"rsParams": {"priority": 1, "hidden": False}})
        self.assertEqual(len(self.rs.hidden(repl_id)), 0)
        self.assertFalse(self.rs.member_info(repl_id, hidden['_id'])['rsInfo'].get('hidden', False))


if __name__ == '__main__':
    unittest.main()
