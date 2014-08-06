#!/usr/bin/python
# coding=utf-8

import os
import sys
sys.path.insert(0, '../')

# log_file = os.path.join(os.path.split(__file__)[0], 'test.log')

import logging
# logging.basicConfig(level=logging.DEBUG, filename=log_file)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import tempfile

from lib import set_bin_path, cleanup_storage
from lib.shards import Shard, Shards
from lib.hosts import Hosts
from lib.process import PortPool, HOSTNAME

import time
import operator
import unittest
import pymongo
import re
import subprocess

from nose.plugins.skip import SkipTest
from nose.plugins.attrib import attr

MONGODB_VERSION = re.compile("db version v(\d)+\.(\d)+\.(\d)+")


@attr('shards')
@attr('test')
class ShardsTestCase(unittest.TestCase):
    def setUp(self):
        self.sh = Shards()
        set_bin_path(os.environ.get('MONGOBIN', None))
        PortPool().change_range()

    def tearDown(self):
        # self.sh.cleanup()
        cleanup_storage()

    def test_singleton(self):
        self.assertEqual(id(self.sh), id(Shards()))

    def test_set_settings(self):
        path = os.path.join(os.getcwd(), 'bin')
        self.sh.set_settings(path)
        self.assertEqual(path, self.sh.bin_path)

    def test_bool(self):
        self.assertEqual(False, bool(self.sh))
        self.sh.create({'id': 'sh01'})
        self.assertEqual(True, bool(self.sh))

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
        shard.cleanup()

    def test_operations2(self):
        self.assertTrue(len(self.sh) == 0)
        config1 = {'id': 'sh01'}
        config2 = {'id': 'sh02'}
        self.sh.create(config1)
        self.sh.create(config2)
        self.assertTrue(len(self.sh) == 2)
        for key in self.sh:
            self.assertTrue(key in ('sh01', 'sh02'))
        for key in ('sh01', 'sh02'):
            self.assertTrue(key in self.sh)

    def test_cleanup(self):
        config1 = {'id': 'sh01'}
        config2 = {'id': 'sh02'}
        self.assertTrue(len(self.sh) == 0)
        self.sh.create(config1)
        self.sh.create(config2)
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
        shard_id = self.sh.create(config)
        self.assertEqual(shard_id, 'shard_cluster_1')
        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)
        result = c.admin.command("listShards")
        for shard in result['shards']:
            shard['_id'] in ('sh01', 'sh02', 'sh-rs-01')
        c.close()

    @attr('auth')
    def test_sh_new_with_auth(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'auth_key': 'secret',
            'login': 'admin',
            'password': 'adminpass',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'}]
        }
        self.sh.create(config)
        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.command, "listShards")
        c.admin.authenticate('admin', 'adminpass')
        self.assertTrue(isinstance(c.admin.command("listShards"), dict))
        c.close()

    def test_sh_del(self):
        sh1_id = self.sh.create({})
        sh2_id = self.sh.create({})
        self.assertEqual(len(self.sh), 2)
        self.sh.remove(sh1_id)
        self.assertEqual(len(self.sh), 1)
        self.sh.remove(sh2_id)
        self.assertEqual(len(self.sh), 0)

    def test_info(self):
        config = {
            'configsvrs': [{}, {}, {}],
            'routers': [{}, {}, {}],
            'members': [{}, {}]
        }
        sh_id = self.sh.create(config)
        info = self.sh.info(sh_id)
        self.assertTrue(isinstance(info, dict))
        for item in ("members", "configsvrs", "routers", "uri", "orchestration"):
            self.assertTrue(item in info)

        self.assertEqual(len(info['members']), 2)
        self.assertEqual(len(info['configsvrs']), 3)
        self.assertEqual(len(info['routers']), 3)
        self.assertTrue(info['uri'].find(','))
        self.assertEqual(info['orchestration'], 'sh')

    def test_configservers(self):
        config = {}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.configservers(sh_id)), 1)
        self.sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.configservers(sh_id)), 3)

    def test_routers(self):
        config = {}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.routers(sh_id)), 1)
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.routers(sh_id)), 3)

    def test_router_add(self):
        config = {}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.routers(sh_id)), 1)
        self.sh.router_add(sh_id, {})
        self.assertEqual(len(self.sh.routers(sh_id)), 2)
        self.sh.router_add(sh_id, {})
        self.assertEqual(len(self.sh.routers(sh_id)), 3)
        self.sh.cleanup()

    def test_members(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}]}
        sh_id = self.sh.create(config)

        self.assertEqual(len(self.sh.members(sh_id)), 0)
        self.sh.cleanup()

        config = {'routers': [{'port': port}], 'members': [{}, {}, {}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.members(sh_id)), 3)

    def test_member_info(self):
        config = {'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    @attr('auth')
    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'admin', 'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    def test_member_del(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}], 'members': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)

        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)
        result = c.admin.command("listShards")

        self.assertEqual(len(result['shards']), 3)

        # remove member-host
        result = self.sh.member_del(sh_id, 'member1')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'member1')
        time.sleep(5)
        result = self.sh.member_del(sh_id, 'member1')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)
        self.assertEqual(result['shard'], 'member1')

        # remove member-replicaset
        result = self.sh.member_del(sh_id, 'sh-rs-01')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh-rs-01')
        time.sleep(7)
        result = self.sh.member_del(sh_id, 'sh-rs-01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)
        self.assertEqual(result['shard'], 'sh-rs-01')

    def test_member_add(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}]}
        sh_id = self.sh.create(config)

        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)

        self.assertEqual(len(c.admin.command("listShards")['shards']), 0)
        result = self.sh.member_add(sh_id, {'id': 'test1', 'shardParams': {}})
        self.assertTrue(result.get('isHost', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)

        result = self.sh.member_add(sh_id, {'id': 'test2', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}})
        self.assertFalse(result.get('isHost', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)


@attr('shards')
@attr('test')
class ShardTestCase(unittest.TestCase):

    def mongod_version(self):
        raw = subprocess.Popen([os.path.join(self.bin_path, 'mongod'), '--version'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).stdout.read()
        m = MONGODB_VERSION.match(raw)
        if m:
            return m.groups()

    def setUp(self):
        self.bin_path = os.environ.get('MONGOBIN', '')
        set_bin_path(self.bin_path)
        PortPool().change_range()

    def tearDown(self):
        if hasattr(self, 'sh') and self.sh is not None:
            self.sh.cleanup()

    def test_len(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh), 0)
        self.sh.member_add('test01', {})
        self.assertEqual(len(self.sh), 1)
        self.sh.member_add('test02', {})
        self.assertEqual(len(self.sh), 2)
        while self.sh.member_remove('test01')['state'] != 'completed':
            time.sleep(1)
        self.assertEqual(len(self.sh), 1)

    def test_sh_new(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'}]
        }
        self.sh = Shard(config)
        c = pymongo.MongoClient(self.sh.router['hostname'])
        for item in c.admin.command("listShards")['shards']:
            self.assertTrue(item['_id'] in ('sh01', 'sh02'))

    @attr('auth')
    def test_sh_new_with_auth(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'auth_key': 'secret',
            'login': 'admin',
            'password': 'adminpass',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'}]
        }
        self.sh = Shard(config)
        c = pymongo.MongoClient(self.sh.router['hostname'])
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.command, "listShards")
        c.admin.authenticate('admin', 'adminpass')
        self.assertTrue(isinstance(c.admin.command("listShards"), dict))
        for item in c.admin.command("listShards")['shards']:
            self.assertTrue(item['_id'] in ('sh01', 'sh02'))

    def test_cleanup(self):
        config = {
            'id': 'shard_cluster_1',
            'configsvrs': [{}],
            'routers': [{}],
            'members': [{'id': 'sh01'}, {'id': 'sh02'},
                        {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}},
                        ]
        }
        self.sh = Shard(config)
        self.assertTrue(len(self.sh) == len(config['members']))
        self.sh.cleanup()
        self.assertTrue(len(self.sh) == 0)

    def test_configsvrs(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.configsvrs), 1)
        self.sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.configsvrs), 3)
        self.sh.cleanup()

    def test_routers(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.routers), 1)
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.routers), 3)
        self.sh.cleanup()

    def test_members(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.members), 0)
        self.sh.cleanup()

        config = {'members': [{}, {}, {}]}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.members), 3)
        self.sh.cleanup()

    def test_router(self):
        config = {}
        self.sh = Shard(config)
        self.assertTrue(Hosts().info(self.sh.router['id'])['statuses']['mongos'])
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        self.sh = Shard(config)
        routers = self.sh.routers
        hostname = routers[1]['hostname']
        _id = routers[1]['id']
        # stop routers 0 and 2
        Hosts().command(routers[0]['id'], 'stop')
        Hosts().command(routers[2]['id'], 'stop')
        router = self.sh.router
        self.assertEqual(router['id'], _id)
        self.assertEqual(router['hostname'], hostname)
        self.sh.cleanup()

    def test_router_add(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.routers), 1)
        self.sh.router_add({})
        self.assertEqual(len(self.sh.routers), 2)
        self.sh.router_add({})
        self.assertEqual(len(self.sh.routers), 3)
        self.sh.cleanup()

    def test_router_command(self):
        config = {'members': [{}, {}]}
        self.sh = Shard(config)
        result = self.sh.router_command('listShards', is_eval=False)
        self.assertEqual(result['ok'], 1)
        self.sh.cleanup()

    def test_member_add(self):
        config = {}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.members), 0)
        result = self.sh.member_add('test1', {})
        self.assertTrue(result.get('isHost', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(self.sh.members), 1)

        result = self.sh.member_add('test2', {'id': 'rs1', 'members': [{}, {}]})
        self.assertFalse(result.get('isHost', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(self.sh.members), 2)

        self.sh.cleanup()

    def test_member_info(self):
        config = {'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = Shard(config)
        info = self.sh.member_info('member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    @attr('auth')
    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'adminpass', 'members': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = Shard(config)
        info = self.sh.member_info('member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isHost'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    def test_member_remove(self):
        config = {'members': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = Shard(config)
        self.assertEqual(len(self.sh.members), 3)

        # remove member-host
        result = self.sh.member_remove('member1')
        self.assertEqual(len(self.sh.members), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'member1')
        time.sleep(5)
        result = self.sh.member_remove('member1')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(self.sh.members), 2)
        self.assertEqual(result['shard'], 'member1')

        # remove member-replicaset
        result = self.sh.member_remove('sh-rs-01')
        self.assertEqual(len(self.sh.members), 2)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh-rs-01')
        time.sleep(7)
        result = self.sh.member_remove('sh-rs-01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(self.sh.members), 1)
        self.assertEqual(result['shard'], 'sh-rs-01')

        self.sh.cleanup()

    def test_info(self):
        config = {
            'configsvrs': [{}, {}, {}],
            'routers': [{}, {}, {}],
            'members': [{}, {}]
        }
        self.sh = Shard(config)
        info = self.sh.info()
        self.assertTrue('members' in info)
        self.assertTrue('configsvrs' in info)
        self.assertTrue('routers' in info)

        self.assertEqual(len(info['members']), 2)
        self.assertEqual(len(info['configsvrs']), 3)
        self.assertEqual(len(info['routers']), 3)

        self.sh.cleanup()

    def test_tagging(self):
        version = self.mongod_version()
        if version and version < ('2', '2', '0'):
            raise SkipTest("mongodb v{version} doesn't support shard tagging".format(version='.'.join(version)))

        tags = ['tag1', 'tag2']
        tags_repl = ['replTag']
        config = {
            'configsvrs': [{}], 'routers': [{}],
            'members': [{'id': 'sh01', 'shardParams': {'tags': tags}},
                        {'id': 'sh02'},
                        {'id': 'sh03', 'shardParams': {'tags': tags_repl, 'members': [{}, {}]}}
                        ]
        }
        self.sh = Shard(config)
        self.assertEqual(tags, self.sh.member_info('sh01')['tags'])
        self.assertEqual([], self.sh.member_info('sh02')['tags'])
        self.assertEqual(tags_repl, self.sh.member_info('sh03')['tags'])

        self.sh.cleanup()


if __name__ == '__main__':
    unittest.main(verbosity=3)
    # suite = unittest.TestSuite()
    # suite.addTest(ShardTestCase('test_sh_new'))
    # suite.addTest(ShardTestCase('test_sh_new_with_auth'))
    # suite.addTest(ShardsTestCase('test_operations'))
    # unittest.TextTestRunner(verbosity=2).run(suite)
