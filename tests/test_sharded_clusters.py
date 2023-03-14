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
import operator
import pymongo
import sys
import time

sys.path.insert(0, '../')

from mongo_orchestration.common import (
    DEFAULT_SUBJECT, DEFAULT_CLIENT_CERT, connected)
from mongo_orchestration.sharded_clusters import ShardedCluster, ShardedClusters
from mongo_orchestration.replica_sets import ReplicaSets
from mongo_orchestration.servers import Servers, Server
from mongo_orchestration.process import PortPool
from tests import (
    certificate, unittest, SkipTest,
    HOSTNAME, TEST_SUBJECT, SERVER_VERSION, SSLTestCase)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_shard(i=0):
    return {
        "id": "sh0%s" % i,
        "shardParams": {
            "members": [{}]
        }
    }


class ShardsTestCase(unittest.TestCase):
    def setUp(self):
        self.sh = ShardedClusters()
        PortPool().change_range()

    def tearDown(self):
        self.sh.cleanup()

    def test_singleton(self):
        self.assertEqual(id(self.sh), id(ShardedClusters()))

    def test_bool(self):
        self.assertEqual(False, bool(self.sh))
        self.sh.create(create_shard())
        self.assertEqual(True, bool(self.sh))

    def test_operations(self):
        config = {'shards': [create_shard(i) for i in range(3)]}
        cluster = ShardedCluster(config)

        self.assertEqual(len(self.sh), 0)
        operator.setitem(self.sh, 1, cluster)
        self.assertEqual(len(self.sh), 1)
        self.assertEqual(operator.getitem(self.sh, 1)['id'], cluster.id)
        operator.delitem(self.sh, 1)
        self.assertEqual(len(self.sh), 0)
        self.assertRaises(KeyError, operator.getitem, self.sh, 1)
        cluster.cleanup()

    def test_operations(self):
        self.assertTrue(len(self.sh) == 0)
        config1 = create_shard(1)
        config2 = create_shard(2)
        self.sh.create(config1)
        self.sh.create(config2)
        self.assertTrue(len(self.sh) == 2)
        for key in self.sh:
            self.assertTrue(key in ('sh01', 'sh02'))
        for key in ('sh01', 'sh02'):
            self.assertTrue(key in self.sh)

    def test_cleanup(self):
        config1 = create_shard(1)
        config2 = create_shard(2)
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
            'shards': [create_shard(1), create_shard(2),
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

    def test_sh_new_with_auth(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'auth_key': 'secret',
            'login': 'admin',
            'password': 'adminpass',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'shards': [create_shard(1), create_shard(2)]
        }
        self.sh.create(config)
        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.command, "listShards")
        c.close()
        c = pymongo.MongoClient(host, username='admin', password='adminpass')
        self.assertTrue(isinstance(c.admin.command("listShards"), dict))
        c.close()

    def test_sh_del(self):
        sh1_id = self.sh.create(create_shard(1))
        sh2_id = self.sh.create(create_shard(2))
        self.assertEqual(len(self.sh), 2)
        self.sh.remove(sh1_id)
        self.assertEqual(len(self.sh), 1)
        self.sh.remove(sh2_id)
        self.assertEqual(len(self.sh), 0)

    def test_info3(self):
        config = {
            'configsvrs': [{}],
            'routers': [{}, {}, {}],
            'shards': [create_shard(1), create_shard(2)]
        }
        sh_id = self.sh.create(config)
        info = self.sh.info(sh_id)
        self.assertTrue(isinstance(info, dict))
        for item in ("shards", "configsvrs", "routers",
                     "mongodb_uri", "orchestration"):
            self.assertTrue(item in info)

        self.assertEqual(len(info['shards']), 2)
        self.assertEqual(len(info['configsvrs']), 1)
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

        config = {'configsvrs': [{}]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.configsvrs(sh_id)), 1)

    def test_routers(self):
        config = create_shard()
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

        config = {'routers': [{'port': port}], 'shards': [create_shard(i) for i in range(3)]}
        sh_id = self.sh.create(config)
        self.assertEqual(len(self.sh.members(sh_id)), 3)

    def test_member_info(self):
        config = {'shards': [create_shard(), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'sh00')
        self.assertEqual(info['id'], 'sh00')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'admin', 'shards': [create_shard(), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)
        info = self.sh.member_info(sh_id, 'sh00')
        self.assertEqual(info['id'], 'sh00')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info(sh_id, 'sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

    def test_member_del(self):
        port = PortPool().port(check=True)
        config = {'routers': [{'port': port}], 'shards': [create_shard(1), create_shard(2), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        sh_id = self.sh.create(config)

        host = "{hostname}:{port}".format(hostname=HOSTNAME, port=port)
        c = pymongo.MongoClient(host)
        result = c.admin.command("listShards")

        self.assertEqual(len(result['shards']), 3)

        # remove member-host
        result = self.sh.member_del(sh_id, 'sh01')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh01')
        time.sleep(5)
        result = self.sh.member_del(sh_id, 'sh01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)
        self.assertEqual(result['shard'], 'sh01')

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
        result = self.sh.member_add(sh_id, create_shard(1))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'sh01')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 1)

        result = self.sh.member_add(sh_id, {'id': 'test2', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}})
        self.assertFalse(result.get('isServer', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(c.admin.command("listShards")['shards']), 2)


class ShardTestCase(unittest.TestCase):

    def setUp(self):
        PortPool().change_range()

    def tearDown(self):
        if hasattr(self, 'sh') and self.sh is not None:
            self.sh.cleanup()

    def test_len(self):
        raise SkipTest("test is not currently working")
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
            'shards': [create_shard(1), create_shard(2)]
        }
        self.sh = ShardedCluster(config)
        c = pymongo.MongoClient(self.sh.router['hostname'])
        for item in c.admin.command("listShards")['shards']:
            self.assertTrue(item['_id'] in ('sh01', 'sh02'))

    def test_sh_new_with_auth(self):
        port = PortPool().port(check=True)
        config = {
            'id': 'shard_cluster_1',
            'auth_key': 'secret',
            'login': 'admin',
            'password': 'adminpass',
            'configsvrs': [{}],
            'routers': [{"port": port}],
            'shards': [create_shard(1), create_shard(2)]
        }
        self.sh = ShardedCluster(config)
        c = pymongo.MongoClient(self.sh.router['hostname'])
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.command, "listShards")
        c.close()
        c = pymongo.MongoClient(self.sh.router['hostname'], username='admin', password='adminpass')
        self.assertTrue(isinstance(c.admin.command("listShards"), dict))
        for item in c.admin.command("listShards")['shards']:
            self.assertTrue(item['_id'] in ('sh01', 'sh02'))
        c.close()

    def test_cleanup(self):
        config = {
            'id': 'shard_cluster_1',
            'configsvrs': [{}],
            'routers': [{}],
            'shards': [create_shard(1),create_shard(2),
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

        config = {'configsvrs': [{}]}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.configsvrs), 1)
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

        config = {'shards': [create_shard(i) for i in range(3)]}
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
        config = {'shards': [create_shard(), create_shard(1)]}
        self.sh = ShardedCluster(config)
        result = self.sh.router_command('listShards', is_eval=False)
        self.assertEqual(result['ok'], 1)
        self.sh.cleanup()

    def test_member_add(self):
        raise SkipTest("test is not currently working")
        config = {}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.members), 0)
        result = self.sh.member_add('test1', {})
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test1')
        self.assertEqual(len(self.sh.members), 1)

        result = self.sh.member_add('test2', {'id': 'rs1', 'members': [{}, {}]})
        self.assertFalse(result.get('isServer', False))
        self.assertTrue(result.get('isReplicaSet', False))
        self.assertEqual(result['id'], 'test2')
        self.assertEqual(len(self.sh.members), 2)

        self.sh.cleanup()

    def test_member_info(self):
        config = {'shards': [create_shard(), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
        info = self.sh.member_info('sh00')
        self.assertEqual(info['id'], 'sh00')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    def test_member_info_with_auth(self):
        config = {'auth_key': 'secret', 'login': 'admin', 'password': 'adminpass', 'shards': [create_shard(), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
        info = self.sh.member_info('sh00')
        self.assertEqual(info['id'], 'sh00')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        info = self.sh.member_info('sh-rs-01')
        self.assertEqual(info['id'], 'sh-rs-01')
        self.assertTrue(info['isReplicaSet'])
        self.assertTrue('_id' in info)

        self.sh.cleanup()

    def test_member_remove(self):
        config = {'shards': [create_shard(1), create_shard(2), {'id': 'sh-rs-01', 'shardParams': {'id': 'rs1', 'members': [{}, {}]}}]}
        self.sh = ShardedCluster(config)
        self.assertEqual(len(self.sh.members), 3)

        # remove member-host
        result = self.sh.member_remove('sh01')
        self.assertEqual(len(self.sh.members), 3)
        self.assertEqual(result['state'], 'started')
        self.assertEqual(result['shard'], 'sh01')
        time.sleep(5)
        result = self.sh.member_remove('sh01')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(len(self.sh.members), 2)
        self.assertEqual(result['shard'], 'sh01')

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
            'configsvrs': [{}],
            'routers': [{}, {}, {}],
            'shards': [create_shard(1), create_shard(2)]
        }
        self.sh = ShardedCluster(config)
        info = self.sh.info()
        self.assertTrue('shards' in info)
        self.assertTrue('configsvrs' in info)
        self.assertTrue('routers' in info)

        self.assertEqual(len(info['shards']), 2)
        self.assertEqual(len(info['configsvrs']), 1)
        self.assertEqual(len(info['routers']), 3)

        self.sh.cleanup()

    def test_tagging(self):
        raise SkipTest("test is not currently working")
        if SERVER_VERSION < (2, 2, 0):
            raise SkipTest("mongodb v{version} doesn't support shard tagging"
                           .format(version='.'.join(map(str, SERVER_VERSION))))

        tags = ['tag1', 'tag2']
        tags_repl = ['replTag']
        config = {
            'configsvrs': [{}], 'routers': [{}],
            'shards': [{'id': 'sh01', 'shardParams': {'tags': tags, 'members': [{}]}},
                        create_shard(2),
                        {'id': 'sh03', 'shardParams': {'tags': tags_repl, 'members': [{}, {}]}}
                        ]
        }
        self.sh = ShardedCluster(config)
        self.assertEqual(tags, self.sh.member_info('sh01')['tags'])
        self.assertEqual([], self.sh.member_info('sh02')['tags'])
        self.assertEqual(tags_repl, self.sh.member_info('sh03')['tags'])

        self.sh.cleanup()

    def test_reset(self):
        raise SkipTest("test is not currently working")
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
        if self.sh.uses_rs_configdb:
            all_hosts.append(ReplicaSets().info(config_id)['mongodb_uri'])
            for member in ReplicaSets().members(config_id):
                Servers().command(member['server_id'], 'stop')
        else:
            all_hosts.append(Servers().hostname(config_id))
            Servers().command(config_id, 'stop')
        router_id = self.sh.routers[0]['id']
        print("router_id=%r" % router_id)
        all_hosts.append(Servers().hostname(router_id))
        Servers().command(router_id, 'stop')

        # Reset the ShardedCluster.
        self.sh.reset()
        # Everything is up.
        for host in all_hosts:
            # No ConnectionFailure/AutoReconnect.
            pymongo.MongoClient(host)

    def test_mongodb_auth_uri(self):
        self.sh = ShardedCluster({
            'login': 'luke', 'password': 'ekul',
            'routers': [{}, {}],
            'shards': [create_shard()]
        })
        self.assertIn('mongodb_auth_uri', self.sh.info())
        auth_uri = self.sh.info()['mongodb_auth_uri']
        hosts = ','.join(r['hostname'] for r in self.sh.routers)
        self.assertIn(hosts, auth_uri)
        self.assertIn('luke:ekul', auth_uri)
        self.assertIn('authSource=admin', auth_uri)

    def test_auth_key_without_login(self):
        self.sh = ShardedCluster({
            'auth_key': 'secret',
            'routers': [{}],
            'shards': [create_shard()]
        })
        self.assertIsNotNone(self.sh.key_file)


class ShardSSLTestCase(SSLTestCase):

    @classmethod
    def setUpClass(cls):
        cls.x509_configsvrs = [
                {'members': [{'procParams': {'clusterAuthMode': 'x509'}}]}]

    def setUp(self):
        self.sh = None
        PortPool().change_range()

    def tearDown(self):
        if self.sh is not None:
            self.sh.cleanup()

    def test_ssl_auth(self):
        raise SkipTest("test is not currently working")
        shard_params = {
            'shardParams': {
                'procParams': {
                    'clusterAuthMode': 'x509',
                    'setParameter': {'authenticationMechanisms': 'MONGODB-X509'}
                },
                'members': [{}]
            }
        }
        config = {
            'login': TEST_SUBJECT,
            'authSource': '$external',
            'configsvrs': self.x509_configsvrs,
            'routers': [{'clusterAuthMode': 'x509'}],
            'shards': [shard_params, shard_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        # Should not raise an Exception.
        self.sh = ShardedCluster(config)

        # Should create an extra user. No raise on authenticate.
        host = self.sh.router['hostname']
        client = pymongo.MongoClient(
            host, tlsCertificateKeyFile=DEFAULT_CLIENT_CERT,
            tlsAllowInvalidCertificates=True, username=DEFAULT_SUBJECT, mechanism='MONGODB-X509')
        client['$external'].command('isMaster')
        client.close()

        # Should create the user we requested. No raise on authenticate.
        client = pymongo.MongoClient(
            host, tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True, username=TEST_SUBJECT, mechanism='MONGODB-X509')
        client['$external'].command('isMaster')
        client.close()

    def test_scram_with_ssl(self):
        proc_params = {'procParams': {'clusterAuthMode': 'x509'}}
        config = {
            'login': 'luke',
            'password': 'ekul',
            'configsvrs': self.x509_configsvrs,
            'routers': [{'clusterAuthMode': 'x509'}],
            'shards': [{'shardParams': {'members': [proc_params]}},
                       {'shardParams': {'members': [proc_params]}}],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }

        # Should not raise an Exception.
        self.sh = ShardedCluster(config)
        time.sleep(1)

        # Should create the user we requested. No raise on authenticate.
        host = self.sh.router['hostname']
        client = pymongo.MongoClient(
            host, tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True, username='luke', password='ekul')
        # This should be the only user.
        self.assertEqual(len(client.admin.command('usersInfo')['users']), 1)
        self.assertFalse(client['$external'].command('usersInfo')['users'])

    def test_ssl(self):
        config = {
            'configsvrs': [{}],
            'routers': [{}],
            'shards': [create_shard(1), create_shard(2)],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        # Should not raise an Exception.
        self.sh = ShardedCluster(config)

        # Server should require SSL.
        host = self.sh.router['hostname']
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            connected(pymongo.MongoClient(host))
        # This shouldn't raise.
        connected(
            pymongo.MongoClient(host, tlsCertificateKeyFile=certificate('client.pem'),
                                tlsAllowInvalidCertificates=True))

    def test_mongodb_auth_uri(self):
        raise SkipTest("test is not currently working")
        if SERVER_VERSION < (2, 4):
            raise SkipTest("Need to be able to set 'authenticationMechanisms' "
                           "parameter to test.")

        shard_params = {
            'shardParams': {
                'procParams': {
                    'clusterAuthMode': 'x509',
                    'setParameter': {'authenticationMechanisms': 'MONGODB-X509'}
                },
                'members': [{}]
            }
        }
        config = {
            'login': TEST_SUBJECT,
            'authSource': '$external',
            'configsvrs': self.x509_configsvrs,
            'routers': [{'clusterAuthMode': 'x509'}],
            'shards': [shard_params, shard_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        self.sh = ShardedCluster(config)
        self.assertIn('mongodb_auth_uri', self.sh.info())
        auth_uri = self.sh.info()['mongodb_auth_uri']
        hosts = ','.join(r['hostname'] for r in self.sh.routers)
        self.assertIn(hosts, auth_uri)
        self.assertIn(TEST_SUBJECT, auth_uri)
        self.assertIn('authSource=$external', auth_uri)
        self.assertIn('authMechanism=MONGODB-X509', auth_uri)


if __name__ == '__main__':
    unittest.main()
