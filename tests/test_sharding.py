# coding=utf-8
import os
import sys
sys.path.insert(0, '../')

log_file = os.path.join(os.path.split(__file__)[0], 'test.log')

import logging
logging.basicConfig(level=logging.DEBUG, filename=log_file)
logger = logging.getLogger(__name__)

import tempfile

from lib import set_storage
from lib.shards import Shard, Shards
from lib.hosts import Hosts
from lib.process import PortPool, HOSTNAME

import time
import operator
import unittest
import pymongo


class ShardsTestCase(unittest.TestCase):
    def setUp(self):
        self.sh = Shards()
        fd, self.db_path = tempfile.mkstemp(prefix='test-shard', suffix='shard.db')
        set_storage(self.db_path, os.environ.get('MONGOBIN', None))
        PortPool().change_range()

    def tearDown(self):
        self.sh.cleanup()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_singleton(self):
        self.assertEqual(id(self.sh), id(Shards()))

    def test_set_settings(self):
        path = tempfile.mktemp(prefix="test-set-settings-")
        self.sh._storage.disconnect()
        self.sh.set_settings(path)
        self.assertEqual(path, self.sh.pids_file)

    def test_operations(self):
        config = {'members': [{}, {}, {}]}
        shard = Shard(config)

        self.assertEqual(len(self.sh), 0)
        operator.setitem(self.sh, 1, shard)
        self.assertEqual(len(self.sh), 1)
        self.assertEqual(operator.getitem(self.sh, 1)['id'], shard.id)
        operator.delitem(self.sh, 1)
        self.assertEqual(len(self.sh), 0)
        self.assertRaises(KeyError, operator.getitem, self.sh, 1)

    def test_operations2(self):
        self.assertTrue(len(self.sh) == 0)
        config1 = {'id': 'sh01'}
        config2 = {'id': 'sh02'}
        self.sh.sh_new(config1)
        self.sh.sh_new(config2)
        self.assertTrue(len(self.sh) == 2)
        for key in self.sh:
            self.assertTrue(key in ('sh01', 'sh02'))
        for key in ('sh01', 'sh02'):
            self.assertTrue(key in self.sh)

    def test_cleanup(self):
        config1 = {'id': 'sh01'}
        config2 = {'id': 'sh02'}
        self.assertTrue(len(self.sh) == 0)
        self.sh.sh_new(config1)
        self.sh.sh_new(config2)
        self.assertTrue(len(self.sh) == 2)
        self.sh.cleanup()
        self.assertTrue(len(self.sh) == 0)

    def test_sh_new(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'},
                        {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}},
                        ]
        }
        shard_id = self.sh.sh_new(config)
        self.assertEqual(shard_id, 'shard_cluster_1')
        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.Connection(host)
        result = c.admin.command("listShards")
        for shard in result['shards']:
            shard['_id'] in ('sh01', 'sh02', 'sh-rs-01')
        c.close()

    def test_sh_del(self):
        sh1_id = self.sh.sh_new({})
        sh2_id = self.sh.sh_new({})
        self.assertEqual(len(self.sh), 2)
        self.sh.sh_del(sh1_id)
        self.assertEqual(len(self.sh), 1)
        self.sh.sh_del(sh2_id)
        self.assertEqual(len(self.sh), 0)

    def test_sh_info(self):
        config = {
            'configsvrs': [{}, {}, {}],
            'routers': [{}, {}, {}],
            'members': [{}, {}]
        }
        sh_id = self.sh.sh_new(config)
        info = self.sh.sh_info(sh_id)
        self.assertTrue('members' in info)
        self.assertTrue('configsvrs' in info)
        self.assertTrue('routers' in info)

        self.assertEqual(len(info['members']), 2)
        self.assertEqual(len(info['configsvrs']), 3)
        self.assertEqual(len(info['routers']), 3)

    def test_sh_configservers(self):
        config = {}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_configservers(sh_id)), 1)
        self.sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_configservers(sh_id)), 3)

    def test_sh_routers(self):
        config = {}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_routers(sh_id)), 1)
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_routers(sh_id)), 3)

    def test_sh_router_add(self):
        config = {}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_routers(sh_id)), 1)
        self.sh.sh_router_add(sh_id, {})
        self.assertEqual(len(self.sh.sh_routers(sh_id)), 2)
        self.sh.sh_router_add(sh_id, {})
        self.assertEqual(len(self.sh.sh_routers(sh_id)), 3)
        self.sh.cleanup()

    def test_sh_members(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}]}
        sh_id = self.sh.sh_new(config)

        self.assertEqual(len(self.sh.sh_members(sh_id)), 0)
        self.sh.cleanup()

        config = {'routers': [{'port': port}], 'members': [{}, {}, {}]}
        sh_id = self.sh.sh_new(config)
        self.assertEqual(len(self.sh.sh_members(sh_id)), 3)

    def test_sh_member_info(self):
        config = {'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.sh_new(config)
        info = self.sh.sh_member_info(sh_id, 'member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])

        info = self.sh.sh_member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])

    def test_sh_member_del(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}], 'members': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.sh_new(config)

        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.Connection(host)
        result = c.admin.command("listShards")

        self.assertEqual(len(result['shards']), 3)

        # remove member-host
        result = self.sh.sh_member_del(sh_id, 'member1')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'member1')
        time.sleep(5)
        result = self.sh.sh_member_del(sh_id, 'member1')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)
        self.assertEqual(result['shard'], 'member1')

        # remove member-replicaset
        result = self.sh.sh_member_del(sh_id, 'sh-rs-01')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh-rs-01')
        time.sleep(7)
        result = self.sh.sh_member_del(sh_id, 'sh-rs-01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)
        self.assertEqual(result['shard'], 'sh-rs-01')

    def test_sh_member_add(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}]}
        sh_id = self.sh.sh_new(config)

        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.Connection(host)

        self.assertEqual(len(c.admin.command("listShards")['shards']), 0)
        result = self.sh.sh_member_add(sh_id, {'id': 'test1', 'shardParams': {}})
        self.assertTrue(result.get('isHost', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)

        result = self.sh.sh_member_add(sh_id, {'id': 'test2', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}})
        self.assertFalse(result.get('isHost', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)


class ShardTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix='test-shard', suffix='shard.db')
        set_storage(self.db_path, os.environ.get('MONGOBIN', None))
        PortPool().change_range()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_len(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh), 0)
        sh.member_add('test01', {})
        self.assertEqual(len(sh), 1)
        sh.member_add('test02', {})
        self.assertEqual(len(sh), 2)
        while sh.member_remove('test01')['state'] != 'completed':
            time.sleep(1)
        self.assertEqual(len(sh), 1)

        sh.cleanup()

    def test_cleanup(self):
        config = {
            'id': 'shard_cluster_1',
            'configsvrs': [{}],
            'routers': [{}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'},
                        {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}},
                        ]
        }
        sh = Shard(config)
        self.assertTrue(len(sh) == len(config['members']))
        sh.cleanup()
        self.assertTrue(len(sh) == 0)

    def test_configsvrs(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh.configsvrs), 1)
        sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        sh = Shard(config)
        self.assertEqual(len(sh.configsvrs), 3)
        sh.cleanup()

    def test_routers(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh.routers), 1)
        sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        sh = Shard(config)
        self.assertEqual(len(sh.routers), 3)
        sh.cleanup()

    def test_members(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh.members), 0)
        sh.cleanup()

        config = {'members': [{}, {}, {}]}
        sh = Shard(config)
        self.assertEqual(len(sh.members), 3)
        sh.cleanup()

    def test_router(self):
        config = {}
        sh = Shard(config)
        self.assertTrue(Hosts().h_info(sh.router['id'])['statuses']['mongos'])
        sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        sh = Shard(config)
        routers = sh.routers
        hostname = routers[1]['hostname']
        _id = routers[1]['id']
        # stop routers 0 and 2
        Hosts().h_command(routers[0]['id'], 'stop')
        Hosts().h_command(routers[2]['id'], 'stop')
        router = sh.router
        self.assertEqual(router['id'], _id)
        self.assertEqual(router['hostname'], hostname)
        sh.cleanup()

    def test_router_add(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh.routers), 1)
        sh.router_add({})
        self.assertEqual(len(sh.routers), 2)
        sh.router_add({})
        self.assertEqual(len(sh.routers), 3)
        sh.cleanup()

    def test_router_command(self):
        config = {'members': [{}, {}]}
        sh = Shard(config)
        result = sh.router_command('listShards', is_eval=False)
        self.assertEqual(result['ok'], 1)
        sh.cleanup()

    def test_member_add(self):
        config = {}
        sh = Shard(config)
        self.assertEqual(len(sh.members), 0)
        result = sh.member_add('test1', {})
        self.assertTrue(result.get('isHost', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(sh.members), 1)

        result = sh.member_add('test2', {'id': 'rs1', 'members': [{}, {}]})
        self.assertFalse(result.get('isHost', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(sh.members), 2)

        sh.cleanup()

    def test_member_info(self):
        config = {'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh = Shard(config)
        info = sh.member_info('member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])

        info = sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])

        sh.cleanup()

    def test_member_remove(self):
        config = {'members': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh = Shard(config)
        self.assertEqual(len(sh.members), 3)

        # remove member-host
        result = sh.member_remove('member1')
        self.assertEqual(len(sh.members), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'member1')
        time.sleep(5)
        result = sh.member_remove('member1')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(sh.members), 2)
        self.assertEqual(result['shard'], 'member1')

        # remove member-replicaset
        result = sh.member_remove('sh-rs-01')
        self.assertEqual(len(sh.members), 2)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh-rs-01')
        time.sleep(7)
        result = sh.member_remove('sh-rs-01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(sh.members), 1)
        self.assertEqual(result['shard'], 'sh-rs-01')

        sh.cleanup()

    def test_info(self):
        config = {
            'configsvrs': [{}, {}, {}],
            'routers': [{}, {}, {}],
            'members': [{}, {}]
        }
        sh = Shard(config)
        info = sh.info()
        self.assertTrue('members' in info)
        self.assertTrue('configsvrs' in info)
        self.assertTrue('routers' in info)

        self.assertEqual(len(info['members']), 2)
        self.assertEqual(len(info['configsvrs']), 3)
        self.assertEqual(len(info['routers']), 3)

        sh.cleanup()

if __name__ == '__main__':
    unittest.main()
