#!/usr/bin/python
# coding=utf-8

import os
import sys
sys.path.insert(0, '../')

log_file = os.path.join(os.path.split(__file__)[0], 'test.log')

import logging
logging.basicConfig(level=logging.DEBUG, filename=log_file)
logger = logging.getLogger(__name__)


import unittest
from lib.rs import ReplicaSet, RS
from lib.hosts import Hosts
from lib.process import PortPool, HOSTNAME
import pymongo

import operator
import tempfile
import time


class RSTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.path = tempfile.mktemp(prefix="test-rs")
        self.rs = RS()
        self.rs.set_settings(self.path, os.environ.get('MONGOBIN', None))

    def tearDown(self):
        self.rs.cleanup()
        self.rs._storage.disconnect()
        if os.path.exists(self.path):
            os.remove(self.path)

    def waiting(self, fn, timeout=300, sleep=10):
        t_start = time.time()
        while not fn():
            if time.time() - t_start > timeout:
                return False
            time.sleep(sleep)
        return True

    def test_singleton(self):
        self.assertEqual(id(self.rs), id(RS()))

    def test_set_settings(self):
        path = tempfile.mktemp(prefix="test-set-settings-")
        self.rs._storage.disconnect()
        self.rs.set_settings(path)
        self.assertEqual(path, self.rs.pids_file)

    def test_bool(self):
        self.assertEqual(False, bool(self.rs))
        self.rs.rs_new({'id': 'test-rs-1', 'members': [{}, {}]})
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
        self.rs.rs_new({'id': 'test-rs-1', 'members': [{}, {}]})
        self.rs.rs_new({'id': 'test-rs-2', 'members': [{}, {}]})
        self.assertTrue(len(self.rs) == 2)
        for key in self.rs:
            self.assertTrue(key in ('test-rs-1', 'test-rs-2'))
        for key in ('test-rs-1', 'test-rs-2'):
            self.assertTrue(key in self.rs)

    def test_cleanup(self):
        self.assertTrue(len(self.rs) == 0)
        self.rs.rs_new({'id': 'test-rs-1', 'members': [{}, {}]})
        self.rs.rs_new({'id': 'test-rs-2', 'members': [{}, {}]})
        self.assertTrue(len(self.rs) == 2)
        self.rs.cleanup()
        self.assertTrue(len(self.rs) == 0)

    def test_rs_new(self):
        port1, port2 = PortPool().port(check=True), PortPool().port(check=True)
        repl_id = self.rs.rs_new({'id': 'test-rs-1',
                                  'members': [{"procParams": {"port": port1}},
                                              {"procParams": {"port": port2}}
                                              ]})
        self.assertEqual(repl_id, 'test-rs-1')
        host1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        host2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        c = pymongo.Connection([host1, host2], replicaSet=repl_id)
        self.assertEqual(c.admin.eval("rs.conf()")['_id'], repl_id)
        c.close()

    def test_repl_info(self):
        repl_id = self.rs.rs_new({'id': 'test-rs-1', 'members': [{}, {}]})
        info = self.rs.repl_info(repl_id)
        self.assertTrue(isinstance(info, dict))
        self.assertEqual(info['id'], repl_id)
        self.assertEqual(len(info['members']), 2)

    def test_rs_primary(self):
        repl_id = self.rs.rs_new({'id': 'test-rs-1', 'members': [{}, {}]})
        primary = self.rs.rs_primary(repl_id)['uri']
        c = pymongo.Connection(primary)
        self.assertTrue(c.is_primary)
        c.close()

    def test_rs_primary_stepdown(self):
        repl_id = self.rs.rs_new({'id': 'test-rs-stepdown', 'members': [{}, {}, {"rsParams": {"priority": 1.4}}]})
        primary = self.rs.rs_primary(repl_id)['uri']
        self.rs.rs_primary_stepdown(repl_id, timeout=60)
        self.assertTrue(self.waiting(timeout=80, sleep=5, fn=lambda: primary != self.rs.rs_primary(repl_id)['uri']))
        self.assertNotEqual(primary, self.rs.rs_primary(repl_id)['uri'])

    def test_rs_del(self):
        self.rs.rs_new({'members': [{}, {}]})
        repl_id = self.rs.rs_new({'members': [{}, {}]})
        self.assertEqual(len(self.rs), 2)
        primary = self.rs.rs_primary(repl_id)['uri']
        self.assertTrue(pymongo.Connection(primary))
        self.rs.rs_del(repl_id)
        self.assertEqual(len(self.rs), 1)
        self.assertRaises(pymongo.errors.AutoReconnect, pymongo.Connection, primary)

    def test_rs_members(self):
        port1, port2 = PortPool().port(check=True), PortPool().port(check=True)
        host1 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port1)
        host2 = "{hostname}:{port}".format(hostname=HOSTNAME, port=port2)
        repl_id = self.rs.rs_new({'members': [{"procParams": {"port": port1}}, {"procParams": {"port": port2}}]})
        members = self.rs.rs_members(repl_id)
        self.assertEqual(len(members), 2)
        self.assertTrue(host1 in [member['host'] for member in members])
        self.assertTrue(host2 in [member['host'] for member in members])

    def test_rs_secondaries(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}, {}]})
        secondaries = self.rs.rs_secondaries(repl_id)
        self.assertEqual(len(secondaries), 2)

    def test_rs_arbiters(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}, {"rsParams": {"arbiterOnly": True}}]})
        arbiters = self.rs.rs_arbiters(repl_id)
        self.assertEqual(len(arbiters), 1)

    def test_rs_hidden(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}, {"rsParams": {"priority":0, "hidden": True}}]})
        hidden = self.rs.rs_hidden(repl_id)
        self.assertEqual(len(hidden), 1)

    def test_rs_member_info(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {"rsParams": {"arbiterOnly": True}}, {"rsParams": {"priority":0, "hidden": True}}]})
        info = self.rs.rs_member_info(repl_id, 0)
        for key in ('procInfo', 'uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 0)
        self.assertTrue(info['statuses']['primary'])

        info = self.rs.rs_member_info(repl_id, 1)
        for key in ('procInfo', 'uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 1)
        self.assertTrue(info['rsInfo']['arbiterOnly'])

        info = self.rs.rs_member_info(repl_id, 2)
        for key in ('procInfo', 'uri', 'statuses', 'rsInfo'):
            self.assertTrue(key in info)
        self.assertEqual(info['_id'], 2)
        self.assertTrue(info['rsInfo']['hidden'])

    def test_rs_member_del(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}, {}]})
        self.assertEqual(len(self.rs.rs_members(repl_id)), 3)
        secondary = self.rs.rs_secondaries(repl_id)[0]
        self.assertTrue(pymongo.Connection(secondary['host']))
        self.assertTrue(self.rs.rs_member_del(repl_id, secondary['_id']))
        self.assertEqual(len(self.rs.rs_members(repl_id)), 2)
        self.assertRaises(pymongo.errors.AutoReconnect, pymongo.Connection, secondary['host'])

    def test_rs_member_add(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}]})
        self.assertEqual(len(self.rs.rs_members(repl_id)), 2)
        member_id = self.rs.rs_member_add(repl_id, {"rsParams": {"priority": 0, "hidden": True}})
        self.assertEqual(len(self.rs.rs_members(repl_id)), 3)
        info = self.rs.rs_member_info(repl_id, member_id)
        self.assertTrue(info['rsInfo']['hidden'])

    def test_rs_member_command(self):
        _id = 1
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {}]})
        self.assertTrue(self.rs.rs_member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.rs_member_command(repl_id, _id, 'stop')
        self.assertFalse(self.rs.rs_member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.rs_member_command(repl_id, _id, 'start')
        self.assertTrue(self.rs.rs_member_info(repl_id, _id)['procInfo']['alive'])
        self.rs.rs_member_command(repl_id, _id, 'restart')
        self.assertTrue(self.rs.rs_member_info(repl_id, _id)['procInfo']['alive'])

    def test_rs_member_update(self):
        repl_id = self.rs.rs_new({'members': [{"rsParams": {"priority": 1.5}}, {"rsParams": {"priority":0, "hidden": True}}, {}]})
        hidden = self.rs.rs_hidden(repl_id)[0]
        self.assertTrue(self.rs.rs_member_info(repl_id, hidden['_id'])['rsInfo']['hidden'])
        self.rs.rs_member_update(repl_id, hidden['_id'], {"rsParams": {"priority": 1, "hidden": False}})
        self.assertEqual(len(self.rs.rs_hidden(repl_id)), 0)
        self.assertFalse(self.rs.rs_member_info(repl_id, hidden['_id'])['rsInfo'].get('hidden', False))


class ReplicaSetTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        fd, self.db_path = tempfile.mkstemp(prefix='test-replica-set', suffix='host.db')
        self.hosts = Hosts()
        self.hosts.set_settings(self.db_path, os.environ.get('MONGOBIN', None))
        self.repl_cfg = {'members': [{}, {}, {'rsParams': {'priority': 0, 'hidden': True}}, {'rsParams': {'arbiterOnly': True}}]}
        self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if len(self.repl) > 0:
            self.repl.cleanup()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

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

    def test_id2host(self):
        members = self.repl.config['members']
        for member in members:
            self.assertTrue(member['host'] == self.repl.id2host(member['_id']))

    def test_host2id(self):
        members = self.repl.config['members']
        for member in members:
            self.assertTrue(member['_id'] == self.repl.host2id(member['host']))

    def test_update_host_map(self):
        origin = self.repl.host_map.copy()
        self.repl.update_host_map(self.repl.config)
        self.assertEqual(self.repl.host_map, origin)

    def test_repl_update(self):
        config = self.repl.config
        config['members'][1]['priority'] = 0
        config['members'][1]['hidden'] = True
        self.assertTrue(self.repl.repl_update(config))
        self.assertTrue(self.repl.config['members'][1]['hidden'])

    def test_repl_info(self):
        cfg = self.repl.config
        info = self.repl.repl_info()
        self.assertEqual(info['auth_key'], self.repl.auth_key)
        self.assertEqual(info['id'], self.repl.repl_id)
        self.assertEqual(len(info['members']), len(cfg['members']))
        members1 = sorted(cfg['members'], key=lambda item: item['_id'])
        members2 = sorted(info['members'], key=lambda item: item['_id'])
        for i in range(len(members1)):
            self.assertEqual(members1[i]['_id'], members2[i]['_id'])
            self.assertEqual(members1[i]['host'], members2[i]['host'])

    def test_repl_member_add(self):
        member_id = self.repl.repl_member_add({"rsParams": {"priority": 0, "hidden": True}})
        self.assertTrue(member_id >= 0)
        member = filter(lambda item: item['_id'] == member_id, self.repl.config['members'])[0]
        self.assertTrue(member['hidden'])

    def test_run_command(self):
        self.assertEqual(self.repl.run_command("rs.status()", is_eval=True)['ok'], 1)
        result = self.repl.run_command('serverStatus', arg=None, is_eval=False, member_id=0)['repl']
        for key in ('me', 'ismaster', 'setName', 'primary', 'hosts'):
            self.assertTrue(key in result)
        self.assertEqual(self.repl.run_command(command="replSetGetStatus", is_eval=False)['ok'], 1)

    def test_config(self):
        config = self.repl.config
        self.assertTrue('_id' in config)
        self.assertTrue('members' in config)

    def test_member_create(self):
        result = self.repl.member_create({}, 13)
        self.assertTrue('host' in result)
        self.assertTrue('_id' in result)
        h_id = Hosts().h_id_by_hostname(result['host'])
        h_info = Hosts().h_info(h_id)
        self.assertEqual(result['host'], h_info['uri'])
        self.assertTrue(h_info['procInfo']['alive'])
        Hosts().h_del(h_id)

    def test_member_del(self):
        m_count = len(self.repl.config['members'])
        self.assertTrue(self.repl.member_del(3))
        self.assertEqual(len(self.repl.config['members']), m_count - 1)

    def test_member_del_no_reconfig(self):
        m_count = len(self.repl.config['members'])
        self.assertTrue(self.repl.member_del(3, reconfig=False))
        self.assertEqual(len(self.repl.config['members']), m_count)
        self.repl.host_map.pop(3)

    def test_member_update(self):
        member = filter(lambda item: item['_id'] == 2, self.repl.config['members'])[0]
        self.assertTrue(member.get('hidden', False))
        self.assertTrue(self.repl.member_update(2, {"rsParams": {"priority": 1, "hidden": False}}))
        member = filter(lambda item: item['_id'] == 2, self.repl.config['members'])[0]
        self.assertFalse(member.get('hidden', False))

    def test_member_info(self):
        member = filter(lambda item: item['_id'] == 3, self.repl.config['members'])[0]
        result = self.repl.member_info(3)
        self.assertTrue(result['procInfo']['alive'])
        self.assertEqual(member['host'], result['uri'])
        self.assertTrue(len(result['rsInfo']) > 0)

    def test_member_command(self):
        _id = 3
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'stop')
        self.assertFalse(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'start')
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])
        self.repl.member_command(_id, 'restart')
        self.assertTrue(self.repl.member_info(_id)['procInfo']['alive'])

    def test_members(self):
        members1 = sorted(self.repl.config['members'], key=lambda item: item['_id'])
        members2 = sorted(self.repl.members(), key=lambda item: item['_id'])
        self.assertEqual(len(members1), len(members2))
        for i in xrange(len(members1)):
            self.assertEqual(members1[i]['host'], members2[i]['host'])
            self.assertEqual(members1[i]['_id'], members2[i]['_id'])

    def test_stepdown(self):
        primary = self.repl.primary()
        self.assertTrue(self.repl.stepdown())
        self.assertNotEqual(primary, self.repl.primary())

    def test_primary(self):
        primary = self.repl.primary()
        self.assertTrue(Hosts().h_info(Hosts().h_id_by_hostname(primary))['statuses']['primary'])

    def test_get_members_in_state(self):
        primaries = self.repl.get_members_in_state(1)
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0], self.repl.primary())

    def test_connection(self):
        _id = 2
        self.assertTrue(self.repl.connection(timeout=5))
        self.assertTrue(self.repl.connection(_id, timeout=5))
        self.repl.member_command(_id, 'stop')
        self.assertFalse(self.repl.connection(_id, timeout=5))

    def test_secondaries(self):
        secondaries = [item['host'] for item in self.repl.secondaries()]
        self.assertEqual(secondaries, self.repl.get_members_in_state(2))

    def test_arbiters(self):
        arbiters = [item['host'] for item in self.repl.arbiters()]
        self.assertEqual(arbiters, self.repl.get_members_in_state(7))

    def test_hidden(self):
        for member in self.repl.hidden():
            self.assertTrue(self.repl.run_command('serverStatus', arg=None, is_eval=False, member_id=2)['repl']['hidden'])


if __name__ == '__main__':
    unittest.main()
