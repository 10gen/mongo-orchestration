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
import operator
import pymongo
import re
import subprocess
import sys
import time

sys.path.insert(0, '../')

from mongo_orchestration import set_releases, cleanup_storage
from mongo_orchestration.sharded_clusters import ShardedCluster, ShardedClusters
from mongo_orchestration.replica_sets import ReplicaSets
from mongo_orchestration.servers import Servers
from mongo_orchestration.process import PortPool, HOSTNAME
from nose.plugins.attrib import attr
from tests import unittest, SkipTest

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MONGODB_VERSION = re.compile("db version v(\d)+\.(\d)+\.(\d)+")


@attr('shards')
@attr('test')
class ShardsTestCase(unittest.TestCase):
    def setUp(self):
        self.sh = ShardedClusters()
        set_releases({"default-release": os.environ.get('MONGOBIN', '')},
                     'default-release')
        PortPool().change_range()

    def tearDown(self):
        # self.sh.cleanup()
        cleanup_storage()

    def test_singleton(self):
        self.assertEqual(id(self.sh), id(ShardedClusters()))

    def test_set_settings(self):
        default_release = 'old-release'
        releases = {default_release: os.path.join(os.getcwd(), 'bin')}
        self.sh.set_settings(releases, default_release)
        self.assertEqual(releases, self.sh.releases)
        self.assertEqual(default_release, self.sh.default_release)

    def test_bool(self):
        self.assertEqual(False, bool(self.sh))
        self.sh.create({'id': 'sh01'})
        self.assertEqual(True, bool(self.sh))

    def test_operations(self):
        config = {'shards': [{}, {}, {}]}
        cluster = ShardedCluster(config)

        self.assertEqual(len(self.sh), 0)
        operator.setitem(self.sh, 1, cluster)
        self.assertEqual(len(self.sh), 1)
        self.assertEqual(operator.getitem(self.sh, 1)['id'], cluster.id)
        operator.delitem(self.sh, 1)
        self.assertEqual(len(self.sh), 0)
        self.assertRaises(KeyError, operator.getitem, self.sh, 1)
        cluster.cleanup()

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
            'shards': [{'id': 'sh01'}, {'id': 'sh02'},
                        {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}},
                        ]
        }
        cluster_id = self.sh.create(config)
        self.assertEqual(cluster_id, 'shard_cluster_1')
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
            'shards': [{'id': 'sh01'}, {'id': 'sh02'}]
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
            'shards': [{}, {}]
        }
        sh_id = self.sh.create(config)
        info = self.sh.info(sh_id)
        self.assertTrue(isinstance(info, dict))
        for item in ("shards", "configsvrs", "routers",
                     "mongodb_uri", "orchestration"):
            self.assertTrue(item in info)

        self.assertEqual(len(info['shards']), 2)
        self.assertEqual(len(info['configsvrs']), 3)
        self.assertEqual(len(info['routers']), 3)
        mongodb_uri = info['mongodb_uri']
        for router in info['routers']:
            self.assertIn(Servers().hostname(router['id']), mongodb_uri)
        self.assertTrue(mongodb_uri.find('mongodb://') == 0)
        self.assertEqual(info['orchestration'], 'sharded_clusters')

    def test_configsvrs(self):
        config = {}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.configsvrs(sh_id)), 1)
        self.sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.configsvrs(sh_id)), 3)

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

        config = {'routers': [{'port': port}], 'shards': [{}, {}, {}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.members(sh_id)), 3)

    def test_member_info(self):
        config = {'shards': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isServer'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    @attr('auth')
    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'admin', 'shards': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isServer'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    def test_member_del(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}], 'shards': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
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
        self.assertTrue(result.get('isServer', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)

        result = self.sh.member_add(sh_id, {'id': 'test2', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}})
        self.assertFalse(result.get('isServer', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)


@attr('shards')
@attr('test')
class ShardTestCase(unittest.TestCase):

    def mongod_version(self):
        proc = subprocess.Popen(
            [os.path.join(self.bin_path, 'mongod'), '--version'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        version_raw = str(proc.stdout.read())
        m = MONGODB_VERSION.match(version_raw)
        if m:
            return m.groups()

    def setUp(self):
        self.bin_path = os.environ.get('MONGOBIN', '')
        set_releases({'default-release': self.bin_path},
                     'default-release')
        PortPool().change_range()

    def tearDown(self):
        if hasattr(self, 'sh') and self.sh is not None:
            self.sh.cleanup()

    def test_len(self):
        config = {}
        self.sh = ShardedCluster(config)
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
            'shards': [{'id': 'sh01'}, {'id': 'sh02'}]
        }
        self.sh = ShardedCluster(config)
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
            'shards': [{'id': 'sh01'}, {'id': 'sh02'}]
        }
        self.sh = ShardedCluster(config)
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
            'shards': [{'id': 'sh01'}, {'id': 'sh02'},
                        {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}},
                        ]
        }
        self.sh = ShardedCluster(config)
        self.assertTrue(len(self.sh) == len(config['shards']))
        self.sh.cleanup()
        self.assertTrue(len(self.sh) == 0)

    def test_configsvrs(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.configsvrs), 1)
        self.sh.cleanup()

        config = {'configsvrs': [{}, {}, {}]}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.configsvrs), 3)
        self.sh.cleanup()

    def test_routers(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.routers), 1)
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.routers), 3)
        self.sh.cleanup()

    def test_members(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.members), 0)
        self.sh.cleanup()

        config = {'shards': [{}, {}, {}]}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.members), 3)
        self.sh.cleanup()

    def test_router(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertTrue(Servers().info(self.sh.router['id'])['statuses']['mongos'])
        self.sh.cleanup()

        config = {'routers': [{}, {}, {}]}
        self.sh = ShardedCluster(config)
        routers = self.sh.routers
        hostname = routers[1]['hostname']
        _id = routers[1]['id']
        # stop routers 0 and 2
        Servers().command(routers[0]['id'], 'stop')
        Servers().command(routers[2]['id'], 'stop')
        router = self.sh.router
        self.assertEqual(router['id'], _id)
        self.assertEqual(router['hostname'], hostname)
        self.sh.cleanup()

    def test_router_add(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.routers), 1)
        self.sh.router_add({})
        self.assertEqual(len(self.sh.routers), 2)
        self.sh.router_add({})
        self.assertEqual(len(self.sh.routers), 3)
        self.sh.cleanup()

    def test_router_command(self):
        config = {'shards': [{}, {}]}
        self.sh = ShardedCluster(config)
        result = self.sh.router_command('listShards', is_eval=False)
        self.assertEqual(result['ok'], 1)
        self.sh.cleanup()

    def test_member_add(self):
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.members), 0)
        result = self.sh.member_add('test1', {})
        self.assertTrue(result.get('isServer', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(self.sh.members), 1)

        result = self.sh.member_add('test2', {'id': 'rs1', 'members': [{}, {}]})
        self.assertFalse(result.get('isServer', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(self.sh.members), 2)

        self.sh.cleanup()

    def test_member_info(self):
        config = {'shards': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
        info = self.sh.member_info('member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isServer'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    @attr('auth')
    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'adminpass', 'shards': [{'id': 'member1'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
        info = self.sh.member_info('member1')
        self.assertEqual(info['id'], 'member1')
        self.assertTrue(info['isServer'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    def test_member_remove(self):
        config = {'shards': [{'id': 'member1'}, {'id': 'member2'}, {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
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
            'shards': [{}, {}]
        }
        self.sh = ShardedCluster(config)
        info = self.sh.info()
        self.assertTrue('shards' in info)
        self.assertTrue('configsvrs' in info)
        self.assertTrue('routers' in info)

        self.assertEqual(len(info['shards']), 2)
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
            'shards': [{'id': 'sh01', 'shardParams': {'tags': tags}},
                        {'id': 'sh02'},
                        {'id': 'sh03', 'shardParams': {'tags': tags_repl, 'members': [{}, {}]}}
                        ]
        }
        self.sh = ShardedCluster(config)
        self.assertEqual(tags, self.sh.member_info('sh01')['tags'])
        self.assertEqual([], self.sh.member_info('sh02')['tags'])
        self.assertEqual(tags_repl, self.sh.member_info('sh03')['tags'])

        self.sh.cleanup()

    def test_reset(self):
        all_hosts = []

        # Start a ShardedCluster with 1 router and 1 config server.
        self.sh = ShardedCluster({})
        # Add 1 Server shard and 1 ReplicaSet shard.
        server_id = self.sh.member_add(params={})['_id']
        all_hosts.append(Servers().hostname(server_id))
        repl_id = self.sh.member_add(params={'members': [{}, {}, {}]})['_id']

        # Shut down the standalone.
        Servers().command(server_id, 'stop')
        # Shut down each member of the replica set.
        server_ids = [m['server_id'] for m in ReplicaSets().members(repl_id)]
        for s_id in server_ids:
            Servers().command(s_id, 'stop')
            all_hosts.append(Servers().hostname(s_id))
        # Shut down config server and router.
        config_id = self.sh.configsvrs[0]['id']
        print("config_id=%r" % config_id)
        all_hosts.append(Servers().hostname(config_id))
        router_id = self.sh.routers[0]['id']
        print("router_id=%r" % router_id)
        all_hosts.append(Servers().hostname(router_id))
        Servers().command(config_id, 'stop')
        Servers().command(router_id, 'stop')

        # Reset the ShardedCluster.
        self.sh.reset()
        # Everything is up.
        for host in all_hosts:
            # No ConnectionFailure/AutoReconnect.
            pymongo.MongoClient(host)


if __name__ == '__main__':
    unittest.main(verbosity=3)
    # suite = unittest.TestSuite()
    # suite.addTest(ShardTestCase('test_sh_new'))
    # suite.addTest(ShardTestCase('test_sh_new_with_auth'))
    # suite.addTest(ShardsTestCase('test_operations'))
    # unittest.TextTestRunner(verbosity=2).run(suite)
