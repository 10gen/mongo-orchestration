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

import pymongo

sys.path.insert(0, '../')

from mongo_orchestration.common import (
    connected, DEFAULT_SUBJECT, DEFAULT_CLIENT_CERT)
from mongo_orchestration.replica_sets import ReplicaSet
from mongo_orchestration.servers import Servers
from mongo_orchestration.process import PortPool
from tests import (
    SkipTest, certificate, TEST_SUBJECT, unittest,
    SERVER_VERSION, SSLTestCase, TEST_RELEASES)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReplicaSetTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.servers = Servers()
        self.servers.set_settings(*TEST_RELEASES)
        self.repl_cfg = {'members': [{}, {}, {'rsParams': {'priority': 0, 'hidden': True}}, {'rsParams': {'arbiterOnly': True}}]}
        # self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if hasattr(self, 'repl'):
            self.repl.cleanup()

    def test_len(self):
        raise SkipTest("test is not currently working")
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

    def test_member_id_to_host(self):
        self.repl_cfg = {'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)
        members = self.repl.config['members']
        for member in members:
            host = self.repl.member_id_to_host(member['_id'])
            self.assertEqual(member['host'], host)

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
        result = self.repl.run_command('serverStatus', arg=None, is_eval=False, member_id=0)['repl']
        for key in ('me', 'setName', 'primary', 'hosts'):
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
        h_id = Servers().host_to_server_id(result['host'])
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
        server_id = Servers().host_to_server_id(primary)
        self.assertTrue(Servers().info(server_id)['statuses']['primary'])

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
        hostname = self.repl.member_id_to_host(_id)
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
        all_hosts = [Servers().hostname(server_id) for server_id in server_ids]

        # Shut down all members of the ReplicaSet.
        for server_id in server_ids:
            Servers().command(server_id, 'stop')

        # Reset the ReplicaSet. --- We should be able to connect to all members.
        self.repl.reset()

        for host in all_hosts:
            # No ConnectionFailure/AutoReconnect.
            connected(pymongo.MongoClient(host))

    def test_rs_settings(self):
        if SERVER_VERSION < (2, 4):
            raise SkipTest(
                "Need at least MongoDB >= 2.4 to test replica set settings.")
        self.repl_cfg = {
            'rsSettings': {'heartbeatTimeoutSecs': 20},
            'members': [{}]
        }
        self.repl = ReplicaSet(self.repl_cfg)
        conn = self.repl.connection()
        if SERVER_VERSION >= (2, 8):
            config = conn.admin.command('replSetGetConfig')['config']
        else:
            config = conn.local.system.replset.find_one()
        self.assertEqual(config['settings']['heartbeatTimeoutSecs'], 20)


class ReplicaSetSSLTestCase(SSLTestCase):

    def tearDown(self):
        if hasattr(self, 'repl'):
            self.repl.cleanup()

    def test_ssl_auth(self):
        if SERVER_VERSION < (2, 4):
            raise SkipTest("Need to be able to set 'authenticationMechanisms' "
                           "parameter to test.")

        member_params = {
            'procParams': {
                'clusterAuthMode': 'x509',
                'setParameter': {'authenticationMechanisms': 'MONGODB-X509'}
            }
        }
        self.repl_cfg = {
            'login': TEST_SUBJECT,
            'authSource': '$external',
            'members': [member_params, member_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        # Should not raise an Exception.
        self.repl = ReplicaSet(self.repl_cfg)

        # Should create an extra user. No raise on authenticate.
        client = pymongo.MongoClient(
            self.repl.primary(), tlsCertificateKeyFile=DEFAULT_CLIENT_CERT,
            tlsAllowInvalidCertificates=True, username=DEFAULT_SUBJECT, mechanism='MONGODB-X509')
        client['$external'].command('isMaster)')

        # Should create the user we requested. No raise on authenticate.
        client = pymongo.MongoClient(
            self.repl.primary(), tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True, username=TEST_SUBJECT, mechanism='MONGODB-X509')
        client['$external'].command('isMaster)')

    def test_scram_with_ssl(self):
        member_params = {'procParams': {'clusterAuthMode': 'x509'}}
        self.repl_cfg = {
            'login': 'luke',
            'password': 'ekul',
            'members': [member_params, member_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        # Should not raise an Exception.
        self.repl = ReplicaSet(self.repl_cfg)

        # Should create the user we requested. No raise on authenticate.
        client = pymongo.MongoClient(
            self.repl.primary(), tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True, username='luke', password='ekul')

        # This should be the only user.
        self.assertEqual(len(client.admin.command('usersInfo')['users']), 1)
        self.assertFalse(client['$external'].command('usersInfo')['users'])

    def test_ssl(self):
        member_params = {}
        self.repl_cfg = {
            'members': [member_params, member_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        # Should not raise an Exception.
        self.repl = ReplicaSet(self.repl_cfg)

        # Server should require SSL.
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            connected(pymongo.MongoClient(self.repl.primary()))

        # This shouldn't raise.
        connected(pymongo.MongoClient(
            self.repl.primary(), tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True))

    def test_mongodb_auth_uri(self):
        if SERVER_VERSION < (2, 4):
            raise SkipTest("Need to be able to set 'authenticationMechanisms' "
                           "parameter to test.")

        member_params = {
            'procParams': {
                'clusterAuthMode': 'x509',
                'setParameter': {'authenticationMechanisms': 'MONGODB-X509'}
            }
        }
        self.repl_cfg = {
            'login': TEST_SUBJECT,
            'authSource': '$external',
            'members': [member_params, member_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        self.repl = ReplicaSet(self.repl_cfg)

        self.assertIn('mongodb_auth_uri', self.repl.info())
        repl_auth_uri = self.repl.info()['mongodb_auth_uri']
        hosts = ','.join(m['host'] for m in self.repl.members())
        self.assertIn(hosts, repl_auth_uri)
        self.assertIn(TEST_SUBJECT, repl_auth_uri)
        self.assertIn('authSource=$external', repl_auth_uri)
        self.assertIn('authMechanism=MONGODB-X509', repl_auth_uri)
        replset_param = 'replicaSet=' + self.repl.repl_id
        self.assertIn(replset_param, repl_auth_uri)

    def test_member_info_auth_uri(self):
        member_params = {
            'procParams': {
                'clusterAuthMode': 'x509',
                'setParameter': {'authenticationMechanisms': 'MONGODB-X509'}
            }
        }
        self.repl_cfg = {
            'login': TEST_SUBJECT,
            'authSource': '$external',
            'members': [member_params, member_params],
            'sslParams': {
                'tlsCAFile': certificate('ca.pem'),
                'tlsCertificateKeyFile': certificate('server.pem'),
                'tlsMode': 'requireTLS',
                'tlsAllowInvalidCertificates': True
            }
        }
        self.repl = ReplicaSet(self.repl_cfg)
        for i in range(len(self.repl)):
            member = self.repl.member_info(i)
            self.assertIn('mongodb_auth_uri', member)
            uri = member['mongodb_auth_uri']
            host = Servers().hostname(member['server_id'])
            self.assertIn(host, uri)
            self.assertIn(TEST_SUBJECT, uri)
            self.assertIn('authSource=$external', uri)
            self.assertIn('authMechanism=MONGODB-X509', uri)


class ReplicaSetAuthTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.servers = Servers()
        self.servers.set_settings(*TEST_RELEASES)
        self.repl_cfg = {'auth_key': 'secret', 'login': 'admin', 'password': 'admin', 'members': [{}, {}]}
        self.repl = ReplicaSet(self.repl_cfg)

    def tearDown(self):
        if len(self.repl) > 0:
            self.repl.cleanup()

    def test_auth_connection(self):
        self.assertTrue(isinstance(self.repl.connection().admin.list_collection_names(), list))
        c = pymongo.MongoClient(self.repl.primary(), replicaSet=self.repl.repl_id)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)

    def test_auth_admin(self):
        c = pymongo.MongoClient(self.repl.primary(), replicaSet=self.repl.repl_id)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)
        c.close()
        c = pymongo.MongoClient(self.repl.primary(), replicaSet=self.repl.repl_id, username='admin', password='admin')
        self.assertTrue(isinstance(c.admin.list_collection_names(), list))
        c.close()

    def test_auth_collection(self):
        raise SkipTest("test is not currently working")
        c = pymongo.MongoClient(self.repl.primary(), replicaSet=self.repl.repl_id, username='admin', password='admin')
        c.test_auth.command('createUser', 'user', pwd='userpass', roles=['readWrite'])
        c.close()

        c = pymongo.MongoClient(self.repl.primary(), replicaSet=self.repl.repl_id, username='user', password='userpass')
        db = c.test_auth
        #coll = db.foo.with_options(write_concern=pymongo.WriteConcern(2, 10000))
        self.assertTrue(db.foo.insert_one({'foo': 'bar'}))
        self.assertTrue(isinstance(db.foo.find_one({}), dict))
        c.close()

    def test_auth_arbiter_member_info(self):
        self.repl.cleanup()
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

    def test_mongodb_auth_uri(self):
        self.assertIn('mongodb_auth_uri', self.repl.info())
        rs_auth_uri = self.repl.info()['mongodb_auth_uri']
        hosts = ','.join(m['host'] for m in self.repl.members())
        self.assertIn(hosts, rs_auth_uri)
        self.assertIn('admin:admin', rs_auth_uri)
        self.assertIn('authSource=admin', rs_auth_uri)
        replset_param = 'replicaSet=' + self.repl.repl_id
        self.assertIn(replset_param, rs_auth_uri)

    def test_member_info_auth_uri(self):
        for i in range(len(self.repl)):
            member = self.repl.member_info(i)
            self.assertIn('mongodb_auth_uri', member)
            uri = member['mongodb_auth_uri']
            host = Servers().hostname(member['server_id'])
            self.assertIn(host, uri)
            self.assertIn('admin:admin', uri)
            self.assertIn('authSource=admin', uri)


if __name__ == '__main__':
    unittest.main()
