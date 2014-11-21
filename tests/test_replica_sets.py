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

import logging
import os
import sys
import operator
import time

import pymongo

sys.path.insert(0, '../')

from mongo_orchestration.replica_sets import ReplicaSet, ReplicaSets
from mongo_orchestration.servers import Servers
from mongo_orchestration.process import PortPool, HOSTNAME
from nose.plugins.attrib import attr
from tests import unittest, assert_eventually

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@attr('rs')
@attr('test')
class ReplicaSetsTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.rs = ReplicaSets()
        self.rs.set_settings(os.environ.get('MONGOBIN', None))

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

    def test_set_settings(self):
        default_release = 'old-release'
        releases = {default_release: os.path.join(os.getcwd(), 'bin')}
        self.rs.set_settings(releases, default_release)
        self.assertEqual(releases, self.rs.releases)
        self.assertEqual(default_release, self.rs.default_release)

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
        self.assertEqual(repl_id, 'test-rs-1')
        server1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        server2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        c = pymongo.MongoClient([server1, server2], replicaSet=repl_id)
        self.assertEqual(c.admin.eval("rs.conf()")['_id'], repl_id)
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
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        self.assertTrue(isinstance(c.admin.collection_names(), list))
        c.admin.logout()
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
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
        c = pymongo.MongoClient(primary)
        self.assertTrue(c.is_primary)
        c.close()

    def test_primary_stepdown(self):
        # This tests Server, but only makes sense in the context of a replica set.
        repl_id = self.rs.create(
            {'id': 'test-rs-stepdown',
             'members': [{}, {}, {"rsParams": {"priority": 1.4}}]})
        primary = self.rs.primary(repl_id)
        primary_server = Servers()._storage[primary['server_id']]
        # No Exception.
        primary_server.stepdown()
        self.assertNotEqual(primary['mongodb_uri'],
                            self.rs.primary(repl_id)['mongodb_uri'])

    def test_rs_del(self):
        self.rs.create({'members': [{}, {}]})
        repl_id = self.rs.create({'members': [{}, {}]})
        self.assertEqual(len(self.rs), 2)
        primary = self.rs.primary(repl_id)['mongodb_uri']
        self.assertTrue(pymongo.MongoClient(primary))
        self.rs.remove(repl_id)
        self.assertEqual(len(self.rs), 1)
        self.assertRaises(pymongo.errors.PyMongoError, pymongo.MongoClient, primary)

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
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'slaveDelay': 5}}]}
        repl_id = self.rs.create(config)
        passives = self.rs.passives(repl_id)
        self.assertEqual(len(passives), 1)

    def test_servers(self):
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'slaveDelay': 5}}]}
        repl_id = self.rs.create(config)
        servers = self.rs.servers(repl_id)
        self.assertEqual(len(servers), 1)

    def test_compare_passives_and_servers(self):
        config = {"members": [{},
                              {"rsParams": {"priority": 0}},
                              {"rsParams": {"arbiterOnly": True}},
                              {"rsParams": {"priority": 0, 'hidden': True}},
                              {"rsParams": {"priority": 0, 'slaveDelay': 5}}]}

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
        repl_id = self.rs.create({'members': [{"rsParams": {"priority": 1.5}}, {}, {}]})
        self.assertEqual(len(self.rs.members(repl_id)), 3)
        secondary = self.rs.secondaries(repl_id)[0]
        self.assertTrue(pymongo.MongoClient(secondary['host']))
        self.assertTrue(self.rs.member_del(repl_id, secondary['_id']))
        self.assertEqual(len(self.rs.members(repl_id)), 2)
        self.assertRaises(pymongo.errors.PyMongoError, pymongo.MongoClient, secondary['host'])

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
            self.assertTrue(secondary_server.freeze(10))
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
            "Higher priority secondary never promoted.")

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


@attr('rs')
@attr('test')
class ReplicaSetTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.servers = Servers()
        self.servers.set_settings(os.environ.get('MONGOBIN', None))
        self.repl_cfg = {'members': [{}, {}, {'rsParams': {'priority': 0, 'hidden': True}}, {'rsParams': {'arbiterOnly': True}}]}
        # self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if hasattr(self, 'repl'):
            self.repl.cleanup()

    def test_len(self):
        self.repl = ReplicaSet(self.repl_cfg)
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))
        self.repl.member_del(3)
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']) - 1)
        self.repl.repl_member_add({'rsParams': {'arbiterOnly': True}})
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))

    def test_cleanup(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        self.assertTrue(len(self.repl) == len(self.repl_cfg['members']))
        self.repl.cleanup()
        self.assertTrue(len(self.repl) == 0)

    def test_id2host(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        members = self.repl.config['members']
        for member in members:
            self.assertTrue(member['host'] == self.repl.id2host(member['_id']))

    def test_host2id(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        members = self.repl.config['members']
        for member in members:
            self.assertEqual(member['_id'],
                             self.repl.host2id(member['host']))

    def test_update_server_map(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        origin = self.repl.server_map.copy()
        self.repl.update_server_map(self.repl.config)
        self.assertEqual(self.repl.server_map, origin)

    def test_repl_update(self):
        self.repl_cfg = {'members': [{}, {}, {'rsParams': {'priority': 0, 'hidden': True}}]}
        self.repl = ReplicaSet(self.repl_cfg)
        config = self.repl.config
        config['members'][1]['priority'] = 0
        config['members'][1]['hidden'] = True
        self.assertTrue(self.repl.repl_update(config))
        self.assertTrue(self.repl.config['members'][1]['hidden'])

    def test_info(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        cfg = self.repl.config
        info = self.repl.info()
        self.assertEqual(info['auth_key'], self.repl.auth_key)
        self.assertEqual(info['id'], self.repl.repl_id)
        self.assertEqual(len(info['members']), len(cfg['members']))
        members1 = sorted(cfg['members'], key=lambda item: item['_id'])
        members2 = sorted(info['members'], key=lambda item: item['_id'])
        for i in range(len(members1)):
            self.assertEqual(members1[i]['_id'], members2[i]['_id'])
            self.assertEqual(members1[i]['host'], members2[i]['host'])

    def test_repl_member_add(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        member_id = self.repl.repl_member_add({"rsParams": {"priority": 0, "hidden": True}})
        self.assertTrue(member_id >= 0)
        member = [item for item in self.repl.config['members'] if item['_id'] == member_id][0]
        self.assertTrue(member['hidden'])

    def test_run_command(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        self.assertEqual(self.repl.run_command("rs.status()", is_eval=True)['ok'], 1)
        result = self.repl.run_command('serverStatus', arg=None, is_eval=False, member_id=0)['repl']
        for key in ('me', 'ismaster', 'setName', 'primary', 'hosts'):
            self.assertTrue(key in result)
        self.assertEqual(self.repl.run_command(command="replSetGetStatus", is_eval=False)['ok'], 1)

    def test_config(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        config = self.repl.config
        self.assertTrue('_id' in config)
        self.assertTrue('members' in config)

    def test_member_create(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        result = self.repl.member_create({}, 13)
        self.assertTrue('host' in result)
        self.assertTrue('_id' in result)
        h_id = Servers().id_by_hostname(result['host'])
        h_info = Servers().info(h_id)
        self.assertIn(result['host'], h_info['mongodb_uri'])
        self.assertTrue(h_info['procInfo']['alive'])
        Servers().remove(h_id)

    def test_member_del(self):
        self.repl_cfg = {'members': [{}, {}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        m_count = len(self.repl.config['members'])
        self.assertTrue(self.repl.member_del(2))
        self.assertEqual(len(self.repl.config['members']), m_count - 1)

    def test_member_del_no_reconfig(self):
        self.repl_cfg = {'members': [{}, {}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        m_count = len(self.repl.config['members'])
        self.assertTrue(self.repl.member_del(2, reconfig=False))
        self.assertEqual(len(self.repl.config['members']), m_count)
        self.repl.server_map.pop(2)

    def test_member_update(self):
        self.repl = ReplicaSet(self.repl_cfg)
        member = [item for item in self.repl.config['members'] if item['_id'] == 2][0]
        self.assertTrue(member.get('hidden', False))
        self.assertTrue(self.repl.member_update(2, {"rsParams": {"priority": 1, "hidden": False}}))
        member = [item for item in self.repl.config['members'] if item['_id'] == 2][0]
        self.assertFalse(member.get('hidden', False))

    def test_member_info(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        member = [item for item in self.repl.config['members'] if item['_id'] == 1][0]
        result = self.repl.member_info(1)
        self.assertTrue(result['procInfo']['alive'])
        self.assertIn(member['host'], result['mongodb_uri'])
        self.assertTrue(len(result['rsInfo']) > 0)

    def test_member_command(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        _id = 1
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'stop')
        self.assertFalse(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'start')
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'restart')
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])

    def test_members(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        members1 = sorted(self.repl.config['members'], key=lambda item: item['_id'])
        members2 = sorted(self.repl.members(), key=lambda item: item['_id'])
        self.assertEqual(len(members1), len(members2))
        for i in range(len(members1)):
            self.assertEqual(members1[i]['host'], members2[i]['host'])
            self.assertEqual(members1[i]['_id'], members2[i]['_id'])

    def test_primary(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        primary = self.repl.primary()
        self.assertTrue(Servers().info(Servers().id_by_hostname(primary))['statuses']['primary'])

    def test_get_members_in_state(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        primaries = self.repl.get_members_in_state(1)
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0], self.repl.primary())

    def test_connection(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        _id = 1
        hostname = self.repl.id2host(_id)
        self.assertTrue(self.repl.connection(timeout=5))
        self.assertTrue(self.repl.connection(hostname=hostname, timeout=5))
        self.repl.member_command(_id, 'stop')
        self.assertRaises(pymongo.errors.AutoReconnect, lambda: self.repl.connection(hostname=hostname, timeout=5))

    def test_secondaries(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        secondaries = [item['host'] for item in self.repl.secondaries()]
        self.assertEqual(secondaries, self.repl.get_members_in_state(2))

    def test_arbiters(self):
        self.repl = ReplicaSet(self.repl_cfg)
        arbiters = [item['host'] for item in self.repl.arbiters()]
        self.assertEqual(arbiters, self.repl.get_members_in_state(7))

    def test_hidden(self):
        self.repl = ReplicaSet(self.repl_cfg)
        for _ in self.repl.hidden():
            self.assertTrue(self.repl.run_command('serverStatus', arg=None, is_eval=False, member_id=2)['repl']['hidden'])

    def test_passives(self):
        self.repl = ReplicaSet(self.repl_cfg)
        self.repl.repl_member_add({"rsParams": {"priority": 0}})
        for member in self.repl.passives():
            self.assertTrue(member['host'] in self.repl.run_command('isMaster', is_eval=False).get('passives'))

    def test_servers(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        self.repl.repl_member_add({"rsParams": {"priority": 0}})
        for member in self.repl.servers():
            self.assertTrue(member['host'] in self.repl.run_command('isMaster', is_eval=False).get('hosts'))

    def test_compare_servers_passives(self):
        self.repl = ReplicaSet(self.repl_cfg)
        self.repl.repl_member_add({"rsParams": {"priority": 0}})
        self.repl.repl_member_add({})
        servers = self.repl.servers()
        passives = self.repl.passives()
        for item in servers:
            self.assertTrue(item not in passives)

        for item in passives:
            self.assertTrue(item not in servers)

    def test_wait_while_reachable(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        servers = [member['host'] for member in self.repl.members()]
        self.assertTrue(self.repl.wait_while_reachable(servers, timeout=10))
        self.repl.member_command(1, 'stop')
        self.assertFalse(self.repl.wait_while_reachable(servers, timeout=10))

    def test_reset(self):
        self.repl_cfg = {'members': [{}, {}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)

        server_ids = [m['server_id'] for m in self.repl.members()]
        all_hosts = map(Servers().hostname, server_ids)

        # Shut down all members of the ReplicaSet.
        for server_id in server_ids:
            Servers().command(server_id, 'stop')

        # Reset the ReplicaSet. --- We should be able to connect to all members.
        self.repl.reset()

        for host in all_hosts:
            # No ConnectionFailure/AutoReconnect.
            pymongo.MongoClient(host)


@attr('rs')
@attr('test')
@attr('auth')
class ReplicaSetAuthTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.servers = Servers()
        self.servers.set_settings(os.environ.get('MONGOBIN', None))
        self.repl_cfg = {'auth_key': 'secret', 'login': 'admin', 'password': 'admin', 'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if len(self.repl) > 0:
            self.repl.cleanup()

    def test_auth_connection(self):
        self.assertTrue(isinstance(self.repl.connection().admin.collection_names(), list))
        c = pymongo.MongoReplicaSetClient(self.repl.primary(), replicaSet=self.repl.repl_id)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_admin(self):
        c = pymongo.MongoReplicaSetClient(self.repl.primary(), replicaSet=self.repl.repl_id)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        self.assertTrue(isinstance(c.admin.collection_names(), list))
        self.assertTrue(c.admin.logout() is None)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)

    def test_auth_collection(self):
        c = pymongo.MongoReplicaSetClient(self.repl.primary(), replicaSet=self.repl.repl_id)
        self.assertTrue(c.admin.authenticate('admin', 'admin'))
        db = c.test_auth
        db.add_user('user', 'userpass', roles=['readWrite'])
        c.admin.logout()

        self.assertTrue(db.authenticate('user', 'userpass'))
        self.assertTrue(db.foo.insert({'foo': 'bar'}, w=2, wtimeout=1000))
        self.assertTrue(isinstance(db.foo.find_one(), dict))
        db.logout()
        self.assertRaises(pymongo.errors.OperationFailure, db.foo.find_one)

    def test_auth_arbiter_member_info(self):
        self.repl = ReplicaSet({'members': [
            {}, {'rsParams': {'arbiterOnly': True}}]})
        info = self.repl.member_info(1)
        for key in ('procInfo', 'mongodb_uri', 'statuses', 'rsInfo'):
            self.assertIn(key, info)
        rs_info = info['rsInfo']
        for key in ('primary', 'secondary', 'arbiterOnly'):
            self.assertIn(key, rs_info)
        self.assertFalse(rs_info['primary'])
        self.assertFalse(rs_info['secondary'])
        self.assertTrue(rs_info['arbiterOnly'])


if __name__ == '__main__':
    # unittest.main(verbosity=3)
    suite = unittest.TestSuite()
    suite.addTest(ReplicaSetTestCase('test_member_freeze'))
    suite.addTest(ReplicaSetsTestCase('test_member_freeze'))
    unittest.TextTestRunner(verbosity=2).run(suite)
