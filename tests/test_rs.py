# coding=utf-8
import os
import sys
sys.path.insert(0, '../')

log_file = os.path.join(os.path.split(__file__)[0], 'test.log')

import logging
logging.basicConfig(level=logging.DEBUG, filename=log_file)
logger = logging.getLogger(__name__)


import unittest
from lib.rs import ReplicaSet
from lib.hosts import Hosts
from lib.process import PortPool

import tempfile


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
        self.assertFalse(member.get('hidden', False))
        self.assertTrue(self.repl.member_update(2, {"rsParams": {"priority": 0, "hidden": True}}))
        member = filter(lambda item: item['_id'] == 2, self.repl.config['members'])[0]
        self.assertTrue(member.get('hidden', False))

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
