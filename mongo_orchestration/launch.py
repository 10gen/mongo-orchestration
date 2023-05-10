# Copyright 2023-Present MongoDB, Inc.
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

import atexit
import copy
import itertools
import time
import os
import sys

import pymongo
import requests

# Configurable hosts and ports used in the tests
db_user = str(os.environ.get("DB_USER", ""))
db_password = str(os.environ.get("DB_PASSWORD", ""))

# Document count for stress tests
STRESS_COUNT = 100

# Test namespace, timestamp arguments
TESTARGS = ('test.test', 1)

_mo_address = os.environ.get("MO_ADDRESS", "localhost:8889")
_mongo_start_port = int(os.environ.get("MONGO_PORT", 27017))
_free_port = itertools.count(_mongo_start_port)

DEFAULT_OPTIONS = {
    'logappend': True,
    'ipv6': True,
    'bind_ip': '127.0.0.1,::1',
    # 'storageEngine': 'mmapv1',
    # 'networkMessageCompressors': 'disabled',
    # 'vvvvv': '',
    'setParameter': {'enableTestCommands': 1},  # 'logicalSessionRefreshMillis': 1000000},
}


_post_request_template = {}
if db_user and db_password:
    _post_request_template = {'login': db_user, 'password': db_password}


def _mo_url(resource, *args):
    return 'http://' + '/'.join([_mo_address, resource] + list(args))


@atexit.register
def kill_all():
    try:
        clusters = requests.get(_mo_url('sharded_clusters')).json()
    except requests.ConnectionError as e:
        return
    repl_sets = requests.get(_mo_url('replica_sets')).json()
    servers = requests.get(_mo_url('servers')).json()
    for cluster in clusters['sharded_clusters']:
        requests.delete(_mo_url('sharded_clusters', cluster['id']))
    for rs in repl_sets['replica_sets']:
        requests.delete(_mo_url('relica_sets', rs['id']))
    for server in servers['servers']:
        requests.delete(_mo_url('servers', server['id']))


class MCTestObject(object):

    def proc_params(self):
        params = copy.deepcopy(DEFAULT_OPTIONS)
        params.update(self._proc_params)
        params["port"] = next(_free_port)
        return params

    def get_config(self):
        raise NotImplementedError

    def _make_post_request(self):
        config = _post_request_template.copy()
        config.update(self.get_config())
        import pprint
        pprint.pprint(config)
        ret = requests.post(
            _mo_url(self._resource), timeout=None, json=config)#.json()

        if not ret.ok:
            raise RuntimeError(
                "Error sending POST to cluster: %s" % (ret.text,))

        ret = ret.json()
        if type(ret) == list:  # Will return a list if an error occurred.
            raise RuntimeError("Error sending POST to cluster: %s" % (ret,))
        pprint.pprint(ret)
        return ret

    def _make_get_request(self):
        ret = requests.get(_mo_url(self._resource, self.id), timeout=None)

        if not ret.ok:
            raise RuntimeError(
                "Error sending GET to cluster: %s" % (ret.text,))

        ret = ret.json()
        if type(ret) == list:  # Will return a list if an error occurred.
            raise RuntimeError("Error sending GET to cluster: %s" % (ret,))
        return ret

    def client(self, **kwargs):
        kwargs = kwargs.copy()
        if db_user:
            kwargs['username'] = db_user
            kwargs['password'] = db_password
        client = pymongo.MongoClient(self.uri, **kwargs)
        return client

    def stop(self):
        requests.delete(_mo_url(self._resource, self.id))


class Server(MCTestObject):

    _resource = 'servers'

    def __init__(self, id=None, uri=None, **kwargs):
        self.id = id
        self.uri = uri
        self._proc_params = kwargs

    def get_config(self):
        return {
            'name': 'mongod',
            'procParams': self.proc_params()}

    def start(self):
        if self.id is None:
            try:
                response = self._make_post_request()
            except requests.ConnectionError as e:
                print('Please start mongo-orchestration!')
                sys.exit(1)
            self.id = response['id']
            self.uri = response.get('mongodb_auth_uri',
                                    response['mongodb_uri'])
        else:
            requests.post(
                _mo_url('servers', self.id), timeout=None,
                json={'action': 'start'}
            )
        return self

    def stop(self, destroy=True):
        if destroy:
            super(Server, self).stop()
        else:
            requests.post(_mo_url('servers', self.id), timeout=None,
                          json={'action': 'stop'})


class ReplicaSet(MCTestObject):

    _resource = 'replica_sets'

    def __init__(self, id=None, uri=None, primary=None, secondary=None,
                 single=False, **kwargs):
        self.single = single
        self.id = id
        self.uri = uri
        self.primary = primary
        self.secondary = secondary
        self._proc_params = kwargs
        self.members = []

    def proc_params(self):
        params = super(ReplicaSet, self).proc_params()
        # params.setdefault('setParameter', {}).setdefault('transactionLifetimeLimitSeconds', 3)
        # params.setdefault('setParameter', {}).setdefault('periodicNoopIntervalSecs', 1)
        return params

    def get_config(self):
        members = [{'procParams': self.proc_params()}]
        if not self.single:
            members.extend([
                {'procParams': self.proc_params()},
                {#'rsParams': {'arbiterOnly': True},
                 'procParams': self.proc_params()}
            ])
        return {'members': members}

    def _init_from_response(self, response):
        self.id = response['id']
        self.uri = response.get('mongodb_auth_uri', response['mongodb_uri'])
        for member in response['members']:
            m = Server(member['server_id'], member['host'])
            self.members.append(m)
            if member['state'] == 1:
                self.primary = m
            elif member['state'] == 2:
                self.secondary = m
        return self

    def start(self):
        # We never need to restart a replica set, only start new ones.
        return self._init_from_response(self._make_post_request())

    def restart_primary(self):
        self.primary.stop(destroy=False)
        time.sleep(5)
        self.primary.start()
        time.sleep(1)
        self._init_from_response(self._make_get_request())
        print('New primary: %s' % self.primary.uri)


class ReplicaSetSingle(ReplicaSet):

    def get_config(self):
        return {
            'members': [
                {'procParams': self.proc_params()}
            ]
        }


class ShardedCluster(MCTestObject):

    _resource = 'sharded_clusters'
    _shard_type = ReplicaSet

    def __init__(self, **kwargs):
        self.id = None
        self.uri = None
        self.shards = []
        self._proc_params = kwargs

    def get_config(self):
        return {
            # 'configsvrs': [{'members': [DEFAULT_OPTIONS.copy()]}],
            'routers': [self.proc_params(), self.proc_params()],
            'shards': [
                {'id': 'demo-set-0', 'shardParams':
                    self._shard_type().get_config()},
                # {'id': 'demo-set-1', 'shardParams':
                #     self._shard_type().get_config()}
            ]
        }

    def start(self):
        # We never need to restart a sharded cluster, only start new ones.
        response = self._make_post_request()
        for shard in response['shards']:
            shard_resp = requests.get(_mo_url('replica_sets', shard['_id']))
            shard_json = shard_resp.json()
            self.shards.append(self._shard_type()._init_from_response(shard_json))
        self.id = response['id']
        self.uri = response.get('mongodb_auth_uri', response['mongodb_uri'])
        return self


class ShardedClusterSingle(ShardedCluster):
    _shard_type = ReplicaSetSingle


def argv_has(string):
    return any(string in arg for arg in sys.argv[1:])


DEFAULT_CERTS = os.path.join(
    os.environ.get(
        'MONGO_ORCHESTRATION_HOME', os.path.dirname(__file__)),
    'lib'
)
CERTS = os.environ.get('MONGO_ORCHESTRATION_CERTS', DEFAULT_CERTS)


def main():
    for arg in sys.argv[1:]:
        try:
            port = int(arg)
            _free_port = itertools.count(port)
        except:
            pass
    for version in ['3.6', '4.0', '4.2', '4.4', '5.0', '6.0', '7.0', 'latest']:
        if argv_has(version):
            _post_request_template['version'] = version
            break

    if argv_has('ssl') or argv_has('tls'):
        _post_request_template['sslParams'] = {
            "sslOnNormalPorts": True,
            "sslPEMKeyFile": os.path.join(CERTS, "server.pem"),
            "sslCAFile": os.path.join(CERTS, "ca.pem"),
            "sslWeakCertificateValidation" : True
        }
    if argv_has('auth'):
        _post_request_template['login'] = db_user or 'user'
        _post_request_template['password'] = db_password or 'password'
        _post_request_template['auth_key'] = 'secret'

    single = argv_has('single') or argv_has('standalone') or argv_has('mongod')
    msg = 'Type "q" to quit: '
    if argv_has('repl'):
        # DEFAULT_OPTIONS['enableMajorityReadConcern'] = ''
        cluster = ReplicaSet(single=single)
        msg = 'Type "q" to quit, "r" to shutdown and restart the primary": '
    elif argv_has('shard') or argv_has('mongos'):
        cluster = ShardedClusterSingle()
    elif single:
        cluster = Server()
    else:
        exit('Usage: %s [single|replica|shard] [ssl] [auth]' % (__file__,))

    cluster.start()

    try:
        while True:
            data = input(msg)
            if data == 'q':
                break
            if data == 'r' and argv_has('repl'):
                cluster.restart_primary()
    finally:
        cluster.stop()


# Requires mongo-orchestration running on port 8889.
#
# Usage:
# mongo-launch <single|repl|shard> <auth> <ssl>
#
# Examples (standalone node):
# mongo-launch single
# mongo-launch single auth
# mongo-launch single auth ssl
#
# Sharded clusters:
# mongo-launch shard
# mongo-launch shard auth
# mongo-launch shard auth ssl
#
# Replica sets:
# mongo-launch repl
# mongo-launch repl single
# mongo-launch repl single auth
if __name__ == '__main__':
    main()