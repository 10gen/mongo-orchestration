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

import operator
import os
import socket
import stat
import sys
import tempfile
import time

import pymongo

sys.path.insert(0, '../')

import mongo_orchestration.errors
from mongo_orchestration.common import (
    connected, DEFAULT_SUBJECT, DEFAULT_CLIENT_CERT)
from mongo_orchestration.servers import Server, Servers
from mongo_orchestration.process import PortPool
from tests import (
    SkipTest, certificate, unittest, TEST_SUBJECT, SSLTestCase, SERVER_VERSION,
    TEST_RELEASES)


class ServerVersionTestCase(unittest.TestCase):
    def _test_version_parse(self, version_str, expected_version):
        match = Server.version_patt.search(version_str)
        assert match is not None
        self.assertEqual(expected_version, match.group('version'))

    def test_mongod_2_4_9(self):
        self._test_version_parse("""db version v2.4.9
Wed Aug  3 11:02:33.903 git version: 52fe0d21959e32a5bdbecdc62057db386e4e029c
""", "2.4.9")

    def test_mongos_2_4_9(self):
        self._test_version_parse("""MongoS version 2.4.9 starting: pid=22088 port=27017 64-bit host=As-MBP-2.fios-router.home (--help for usage)
git version: 52fe0d21959e32a5bdbecdc62057db386e4e029c
build sys info: Darwin bs-osx-106-x86-64-2.10gen.cc 10.8.0 Darwin Kernel Version 10.8.0: Tue Jun  7 16:32:41 PDT 2011; root:xnu-1504.15.3~1/RELEASE_X86_64 x86_64 BOOST_LIB_VERSION=1_49
""", "2.4.9")

    def test_mongod_3_3_10(self):
        self._test_version_parse("""db version v3.3.10-262-g2743e90
git version: 2743e906fef318763e753a67967d503b37fcdd07
allocator: system
modules: none
build environment:
    distarch: x86_64
    target_arch: x86_64
""", "3.3.10")

    def test_mongos_3_3_10(self):
        self._test_version_parse("""mongos version v3.3.10-239-g4caf167
git version: 4caf167d193b3b6b4a4cf584f1d903de631a13ef
allocator: system
modules: none
build environment:
    distarch: x86_64
    target_arch: x86_64
""", "3.3.10")


class ServersTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.path = tempfile.mktemp(prefix="test-storage")
        self.servers = Servers()
        self.servers.set_settings(*TEST_RELEASES)

    def remove_path(self, path):
        onerror = lambda func, filepath, exc_info: (os.chmod(filepath, stat.S_IWUSR), func(filepath))
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                time.sleep(2)
                onerror(os.remove, path, None)

    def tearDown(self):
        self.servers.cleanup()
        self.remove_path(self.path)

    def test_singleton(self):
        self.assertEqual(id(self.servers), id(Servers()))

    def test_bool(self):
        self.assertEqual(False, bool(self.servers))
        self.servers.create('mongod', {}, autostart=False)
        self.assertTrue(True, bool(self.servers))

    def test_operations(self):
        server_id = self.servers.create('mongod', {}, autostart=False)
        self.assertTrue(len(self.servers) == 1)
        self.assertTrue(server_id in self.servers)
        server_id2 = 'server-id2'
        server2 = Server(os.path.join(os.environ.get('MONGOBIN', ''), 'mongod'), {})
        server2.start(30)
        server2_pid = server2.info()['procInfo']['pid']
        self.servers[server_id2] = server2
        self.assertTrue(self.servers[server_id2]['procInfo']['pid'] == server2_pid)
        self.assertTrue(server_id2 in self.servers)
        for h_id in self.servers:
            self.assertTrue(h_id in (server_id, server_id2))

        operator.delitem(self.servers, server_id2)
        self.assertFalse(server_id2 in self.servers)
        server2.stop()
        server2.cleanup()

    def test_cleanup(self):
        self.servers.create('mongod', {}, autostart=False)
        self.servers.create('mongod', {}, autostart=True)
        self.assertTrue(len(self.servers) == 2)
        self.servers.cleanup()
        self.assertTrue(len(self.servers) == 0)

    def test_new_server(self):
        self.assertTrue(len(self.servers) == 0)
        server_id = self.servers.create('mongod', {}, autostart=False)
        info = self.servers.info(server_id)
        self.assertTrue(len(self.servers) == 1)
        self.assertNotIn('pid', info['procInfo'])
        server_id2 = self.servers.create('mongod', {}, autostart=True)
        info = self.servers.info(server_id2)
        self.assertTrue(info['procInfo']['pid'] > 0)

        self.assertRaises(mongo_orchestration.errors.TimeoutError, self.servers.create, 'fake_process_', {})

    def test_new_server_with_auth(self):
        server_id = self.servers.create('mongod', {}, login='adminko', password='password', autostart=True)
        hostname = self.servers.hostname(server_id)
        c = pymongo.MongoClient(hostname)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)
        c.close()
        c = pymongo.MongoClient(hostname, username='adminko', password='password')
        self.assertTrue(c.admin.command('isMaster'))
        self.assertTrue(isinstance(c.admin.list_collection_names(), list))
        c.close()

    def test_hdel(self):
        self.assertEqual(len(self.servers), 0)
        h_id = self.servers.create('mongod', {}, autostart=True)
        self.assertEqual(len(self.servers), 1)
        h_info = self.servers.info(h_id)['procInfo']
        self.assertTrue(os.path.exists(h_info['params']['dbpath']))
        self.assertTrue(os.path.exists(h_info['optfile']))
        self.servers.remove(h_id)
        self.assertEqual(len(self.servers), 0)  # check length
        # check cleanup
        self.assertFalse(os.path.exists(h_info['params']['dbpath']))
        self.assertFalse(os.path.exists(h_info['optfile']))

    def test_hcommand(self):
        h_id = self.servers.create('mongod', {}, autostart=False)
        self.assertTrue(self.servers.command(h_id, 'start'))
        self.assertTrue(self.servers.command(h_id, 'stop'))
        self.assertTrue(self.servers.command(h_id, 'start'))
        self.assertTrue(self.servers.command(h_id, 'restart'))
        self.assertRaises(ValueError, self.servers.command, h_id, 'fake')

    def test_hinfo(self):
        h_id = self.servers.create('mongod', {}, autostart=False)
        info = self.servers.info(h_id)
        self.assertEqual(info['id'], h_id)
        self.assertNotIn('pid', info['procInfo'])
        self.assertEqual(info['statuses'], {})
        self.assertEqual(info['serverInfo'], {})

    def test_host_to_server_id(self):
        h_id = self.servers.create('mongod', {}, autostart=True)
        h_uri = self.servers.hostname(h_id)
        h2_id = self.servers.create('mongod', {}, autostart=True)
        h2_uri = self.servers.hostname(h2_id)
        self.assertEqual(self.servers.host_to_server_id(h_uri), h_id)
        self.assertEqual(self.servers.host_to_server_id(h2_uri), h2_id)

    def test_hostname(self):
        h_id = self.servers.create('mongod', {}, autostart=True)
        h_uri = self.servers.hostname(h_id)
        self.assertEqual(self.servers.hostname(h_id), h_uri)

    def test_is_alive(self):
        h_id = self.servers.create('mongod', {}, autostart=True)
        self.assertEqual(self.servers.is_alive(h_id), True)
        self.servers.command(h_id, 'stop')
        self.assertEqual(self.servers.is_alive(h_id), False)

    def test_db_command(self):
        h_id = self.servers.create('mongod', {}, autostart=False)
        self.assertRaises(pymongo.errors.PyMongoError, self.servers.db_command, h_id, 'serverStatus', None, False)
        self.servers.command(h_id, 'start', 10)
        self.assertEqual(self.servers.db_command(h_id, 'serverStatus', arg=None, is_eval=False).get('ok', -1), 1)

    def test_id_specified(self):
        id = 'xyzzy'
        h_id = self.servers.create('mongod', {}, autostart=False, server_id=id)
        self.assertEqual(id, h_id)

    def test_majority_read_concern(self):
        Server.enable_majority_read_concern = True
        server_id = self.servers.create('mongod', {})
        try:
            opts = self.servers.db_command(server_id, 'getCmdLineOpts')
            majority_rc_enabled = (opts
                                   .get('parsed', {})
                                   .get('replication', {})
                                   .get('enableMajorityReadConcern'))
            if SERVER_VERSION >= (3, 2):
                self.assertTrue(majority_rc_enabled)
            else:
                self.assertFalse(majority_rc_enabled)
        finally:
            Server.enable_majority_read_concern = False


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        PortPool().change_range()
        self.mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.server = Server(self.mongod, {})

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.stop()
            self.server.cleanup()

    def test_server(self):
        self.assertTrue(isinstance(self.server, Server))

    def test_init_path(self):
        self.server.cleanup()
        mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        log_dir = os.path.join(tempfile.gettempdir(), os.path.split(tempfile.mktemp())[-1])
        log_path = tempfile.mktemp(dir=log_dir)
        db_path = os.path.join(tempfile.gettempdir(), os.path.split(tempfile.mktemp())[-1])
        self.assertFalse(os.path.exists(log_dir))
        self.assertFalse(os.path.exists(db_path))
        self.server = Server(mongod, {'logpath': log_path, 'dbpath': db_path})
        self.assertTrue(os.path.exists(log_dir))
        self.assertTrue(os.path.exists(db_path))

    def test_mongos(self):
        raise SkipTest("test is not currently working")
        self.server.cleanup()
        del Server.mongod_default['nojournal']
        self.server = Server(self.mongod, {'configsvr': True, 'replSet': True})
        self.server.start(30)
        mongos = os.path.join(os.environ.get('MONGOBIN', ''), 'mongos')
        self.server2 = Server(mongos, {'configdb': self.server.hostname})
        self.assertTrue(self.server2.start())
        self.assertTrue(self.server2.info()['statuses'].get('mongos', False))
        self.server2.stop()
        self.server2.cleanup()

    def test_run_command(self):
        self.server.start(30)

    def test_info(self):
        self.server.start(30)
        info = self.server.info()
        for item in ("mongodb_uri", "statuses", "serverInfo",
                     "procInfo", "orchestration"):
            self.assertTrue(item in info)

        self.assertTrue(info['mongodb_uri'].find(self.server.hostname))
        self.assertTrue(info['mongodb_uri'].find('mongodb://') == 0)
        fd_log, log_path = tempfile.mkstemp()
        os.close(fd_log)
        db_path = tempfile.mkdtemp()
        params = {'logpath': log_path, 'dbpath': db_path}
        server2 = Server(self.mongod, params)
        server2.start()
        info2 = server2.info()
        for param, value in params.items():
            self.assertTrue(info2['procInfo']['params'].get(param, value) == value)
        server2.stop()
        info = server2.info()
        self.assertEqual(len(info['serverInfo']), 0)
        self.assertEqual(len(info['statuses']), 0)
        self.assertEqual(info['orchestration'], 'servers')
        server2.cleanup()

    def test_command(self):
        self.assertRaises(pymongo.errors.PyMongoError, self.server.run_command, 'serverStatus', None, False)
        self.server.start(30)
        self.assertEqual(self.server.run_command('serverStatus', arg=None, is_eval=False).get('ok', -1), 1)

    def test_start(self):
        self.assertNotIn('pid', self.server.info()['procInfo'])
        self.assertTrue(self.server.start(30))
        self.assertTrue(self.server.info()['procInfo']['pid'] > 0)

        fake_server = Server('fake_proc_', {})
        self.assertRaises(mongo_orchestration.errors.TimeoutError, fake_server.start, 5)
        fake_server.cleanup()

    def test_start_with_repair(self):
        self.server.cleanup()
        self.server = Server(self.mongod, {"nojournal": True})
        self.server.start(30)
        os.kill(self.server.pid, 9)
        self.assertTrue(self.server._is_locked)
        self.assertTrue(self.server.start(20))

    def test_stop(self):
        self.assertTrue(self.server.start(60))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server = self.server.hostname.split(':')[0]
        s.connect((server, self.server.cfg['port']))
        self.assertTrue(self.server.stop())
        self.assertRaises(socket.error, s.connect, (server, self.server.cfg['port']))

    def test_restart(self):
        self.assertTrue(self.server.start(30))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server = self.server.hostname.split(':')[0]
        s.connect((server, self.server.cfg['port']))
        s.shutdown(0)
        s.close()
        self.assertTrue(self.server.restart(30))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server, self.server.cfg['port']))
        s.shutdown(0)
        s.close()

    def test_is_alive(self):
        self.server.start()
        self.assertTrue(self.server.is_alive)
        self.server.stop()
        self.assertFalse(self.server.is_alive)
        self.server.restart()
        self.assertTrue(self.server.is_alive)

    def test_set_parameter(self):
        self.server.cleanup()
        cfg = {"setParameter": {"enableTestCommands": 1}}
        self.server = Server(self.mongod, cfg)
        self.server.start()
        c = pymongo.MongoClient(self.server.hostname)
        c.foo.drop_collection('bar')
        c.foo.bar.insert_one({"data": "text stuff"})
        # No Exception.
        c.foo.bar.create_index([("data", pymongo.TEXT)])
        # No Exception.
        c.admin.command("sleep", secs=1)

    def test_cleanup(self):
        self.server.start(80)
        self.assertTrue(os.path.exists(self.server.cfg['dbpath']))
        self.assertTrue(os.path.exists(self.server.config_path))
        self.server.stop()
        self.server.cleanup()
        self.assertFalse(os.path.exists(self.server.cfg['dbpath']))
        self.assertFalse(os.path.exists(self.server.config_path))

    def test_reset(self):
        self.server.stop()
        self.server.reset()
        # No ConnectionFailure.
        connected(pymongo.MongoClient(self.server.hostname))


class ServerSSLTestCase(SSLTestCase):

    def setUp(self):
        self.mongod_name = os.path.join(
            os.environ.get('MONGOBIN', ''), 'mongod')

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.stop()
            self.server.cleanup()

    def test_ssl_auth(self):
        if SERVER_VERSION < (2, 4):
            raise SkipTest("Need to be able to set 'authenticationMechanisms' "
                           "parameter to test.")

        proc_params = {
            'setParameter': {
                'authenticationMechanisms': 'MONGODB-X509'
            }
        }
        ssl_params = {
            'tlsCertificateKeyFile': certificate('server.pem'),
            'tlsCAFile': certificate('ca.pem'),
            'tlsMode': 'requireTLS',
            'tlsAllowInvalidCertificates': True
        }
        # Should not raise an Exception.
        self.server = Server(
            self.mongod_name, proc_params, ssl_params,
            login=TEST_SUBJECT, auth_source='$external')
        self.server.start()
        # Should create an extra user. Doesn't raise.
        client = pymongo.MongoClient(
            self.server.hostname, tlsCertificateKeyFile=DEFAULT_CLIENT_CERT,
            tlsAllowInvalidCertificates=True)
        client['$external'].authenticate(
            DEFAULT_SUBJECT, mechanism='MONGODB-X509')
        # Should also create the user we requested. Doesn't raise.
        client = pymongo.MongoClient(
            self.server.hostname, tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True)
        client['$external'].authenticate(
            TEST_SUBJECT, mechanism='MONGODB-X509')

    def test_scram_with_ssl(self):
        ssl_params = {
            'tlsCertificateKeyFile': certificate('server.pem'),
            'tlsCAFile': certificate('ca.pem'),
            'tlsMode': 'requireTLS',
            'tlsAllowInvalidCertificates': True
        }
        # Should not raise an Exception.
        self.server = Server(
            self.mongod_name, {}, ssl_params, login='luke', password='ekul')
        self.server.start()
        # Should create the user we requested. No raise on authenticate.
        client = pymongo.MongoClient(
            self.server.hostname, tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True)
        client.admin.authenticate('luke', 'ekul')
        # This should be the only user.
        self.assertEqual(len(client.admin.command('usersInfo')['users']), 1)
        self.assertFalse(client['$external'].command('usersInfo')['users'])

    def test_ssl(self):
        ssl_params = {
            'tlsCertificateKeyFile': certificate('server.pem'),
            'tlsCAFile': certificate('ca.pem'),
            'tlsMode': 'requireTLS',
            'tlsAllowInvalidCertificates': True
        }
        # Should not raise an Exception.
        self.server = Server(self.mongod_name, {}, ssl_params)
        self.server.start()
        # Server should require SSL.
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            connected(pymongo.MongoClient(self.server.hostname))
        # Doesn't raise with certificate provided.
        connected(pymongo.MongoClient(
            self.server.hostname, tlsCertificateKeyFile=certificate('client.pem'),
            tlsAllowInvalidCertificates=True))

    def test_mongodb_auth_uri(self):
        if SERVER_VERSION < (2, 4):
            raise SkipTest("Need to be able to set 'authenticationMechanisms' "
                           "parameter to test.")

        proc_params = {
            'setParameter': {
                'authenticationMechanisms': 'MONGODB-X509'
            }
        }
        ssl_params = {
            'tlsCertificateKeyFile': certificate('server.pem'),
            'tlsCAFile': certificate('ca.pem'),
            'tlsMode': 'requireTLS',
            'tlsAllowInvalidCertificates': True
        }
        self.server = Server(
            self.mongod_name, proc_params, ssl_params,
            login=TEST_SUBJECT, auth_source='$external')
        self.server.start()

        self.assertIn('mongodb_auth_uri', self.server.info())
        auth_uri = self.server.info()['mongodb_auth_uri']
        self.assertIn(self.server.hostname, auth_uri)
        self.assertIn(TEST_SUBJECT, auth_uri)
        self.assertIn('authSource=$external', auth_uri)
        self.assertIn('authMechanism=MONGODB-X509', auth_uri)


class ServerAuthTestCase(unittest.TestCase):
    def setUp(self):
        Server.mongod_default['nojournal'] = True
        PortPool().change_range()
        self.mongod = os.path.join(os.environ.get('MONGOBIN', ''), 'mongod')
        self.server = Server(self.mongod, {}, auth_key='secret', login='admin', password='admin')
        self.server.start()

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.stop()
            self.server.cleanup()

    def test_mongodb_auth_uri(self):
        self.assertIn('mongodb_auth_uri', self.server.info())
        auth_uri = self.server.info()['mongodb_auth_uri']
        self.assertIn(self.server.hostname, auth_uri)
        self.assertIn('admin:admin', auth_uri)
        self.assertIn('authSource=admin', auth_uri)

    def test_mongos(self):
        raise SkipTest("test is not currently working")
        self.server.stop()
        self.server.cleanup()
        del Server.mongod_default['nojournal']
        self.server = Server(self.mongod, {'configsvr': True, 'replSet': True}, auth_key='secret')
        self.server.start(30)
        mongos = os.path.join(os.environ.get('MONGOBIN', ''), 'mongos')
        self.server2 = Server(
            mongos, {'configdb': self.server.hostname},
            auth_key='secret', login='admin', password='admin')
        self.server2.start()

        for server in (self.server, self.server2):
            c = pymongo.MongoClient(server.host, server.port)
            self.assertRaises(pymongo.errors.OperationFailure, c.admin.collection_names)
            self.assertTrue(c.admin.authenticate('admin', 'admin'))
            self.assertTrue(isinstance(c.admin.collection_names(), list))
            c.close()

        self.server2.stop()
        self.server2.cleanup()

    def test_auth_connection(self):
        self.assertTrue(isinstance(self.server.connection.admin.list_collection_names(), list))
        c = pymongo.MongoClient(self.server.host, self.server.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)
        self.server.restart()
        c = pymongo.MongoClient(self.server.host, self.server.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)

    def test_auth_admin(self):
        c = pymongo.MongoClient(self.server.host, self.server.port)
        self.assertRaises(pymongo.errors.OperationFailure, c.admin.list_collection_names)
        c.close()
        c = pymongo.MongoClient(self.server.host, self.server.port, username='admin', password='admin')
        self.assertTrue(c.admin.command('isMaster'))
        self.assertTrue(isinstance(c.admin.list_collection_names(), list))
        c.close()

    def test_auth_collection(self):
        c = pymongo.MongoClient(self.server.host, self.server.port, username='admin', password='admin')
        self.assertTrue(bool(c.admin.command('ping')['ok']))
        db = c.test_server_auth
        db.command('createUser', 'user', pwd='userpass', roles=['readWrite'])
        c.close()

        c = pymongo.MongoClient(self.server.host, self.server.port, username='admin', password='admin')
        db = c.test_server_auth
        self.assertTrue(db.foo.insert_one({'foo': 'bar'}))
        self.assertTrue(isinstance(db.foo.find_one(), dict))
        c.close()

if __name__ == '__main__':
    unittest.main()
