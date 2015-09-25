#!/usr/bin/python
# coding=utf-8
# Copyright 2014 MongoDB, Inc.
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

import collections
import copy
import json
import os
import ssl
import stat
import tempfile

WORK_DIR = os.environ.get('MONGO_ORCHESTRATION_HOME', os.getcwd())
PID_FILE = os.path.join(WORK_DIR, 'server.pid')
LOG_FILE = os.path.join(WORK_DIR, 'server.log')

DEFAULT_BIND = os.environ.get('MO_HOST', 'localhost')
DEFAULT_PORT = int(os.environ.get('MO_PORT', '8889'))
DEFAULT_SERVER = 'cherrypy'
DEFAULT_SOCKET_TIMEOUT = 20000  # 20 seconds.

# Username for included client x509 certificate.
DEFAULT_SUBJECT = (
    'C=US,ST=New York,L=New York City,O=MongoDB,OU=KernelUser,'
    'CN=mongo_orchestration'
)
DEFAULT_CLIENT_CERT = os.path.join(
    os.environ.get(
        'MONGO_ORCHESTRATION_HOME', os.path.dirname(__file__)),
    'lib',
    'client.pem'
)
DEFAULT_SSL_OPTIONS = {
    'ssl': True,
    'ssl_certfile': DEFAULT_CLIENT_CERT,
    'ssl_cert_reqs': ssl.CERT_NONE
}


class BaseModel(object):
    """Base object for Server, ReplicaSet, and ShardedCluster."""

    _user_role_documents = [
        {'role': 'userAdminAnyDatabase', 'db': 'admin'},
        {'role': 'clusterAdmin', 'db': 'admin'},
        {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
        {'role': 'readWriteAnyDatabase', 'db': 'admin'}
    ]
    socket_timeout = DEFAULT_SOCKET_TIMEOUT

    @property
    def key_file(self):
        """Get the path to the key file containig our auth key, or None."""
        if self.auth_key:
            key_file_path = os.path.join(tempfile.mkdtemp(), 'key')
            with open(key_file_path, 'w') as fd:
                fd.write(self.auth_key)
            os.chmod(key_file_path, stat.S_IRUSR)
            return key_file_path

    def _strip_auth(self, proc_params):
        """Remove options from parameters that cause auth to be enabled."""
        params = proc_params.copy()
        params.pop("auth", None)
        params.pop("clusterAuthMode", None)
        return params

    def mongodb_auth_uri(self, hosts):
        """Get a connection string with all info necessary to authenticate."""
        parts = ['mongodb://']
        if self.login:
            parts.append(self.login)
            if self.password:
                parts.append(':' + self.password)
            parts.append('@')
        parts.append(hosts + '/')
        if self.login:
            parts.append('?authSource=' + self.auth_source)
            if self.x509_extra_user:
                parts.append('&authMechanism=MONGODB-X509')
        return ''.join(parts)

    def _get_server_version(self, client):
        return tuple(client.admin.command('buildinfo')['versionArray'])

    def _user_roles(self, client):
        server_version_tuple = self._get_server_version(client)
        if server_version_tuple < (2, 6):
            # MongoDB 2.4 roles are an array of strs like ['clusterAdmin', ...].
            return [role['role'] for role in self._user_role_documents]
        return self._user_role_documents

    def _add_users(self, db):
        """Add given user, and extra x509 user if necessary."""
        if self.x509_extra_user:
            # Build dict of kwargs to pass to add_user.
            auth_dict = {
                'name': DEFAULT_SUBJECT,
                'roles': self._user_roles(db.client)
            }
            db.add_user(**auth_dict)
            # Fix kwargs to MongoClient.
            self.kwargs['ssl_certfile'] = DEFAULT_CLIENT_CERT

        # Add secondary user given from request.

        secondary_login = {
            'name': self.login,
            'roles': self._user_roles(db.client)
        }
        if self.password:
            secondary_login['password'] = self.password
        db.add_user(**secondary_login)


def connected(client):
    # Await connection in PyMongo 3.0.
    client.admin.command('ismaster')
    return client


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def preset_merge(data, cluster_type):
    preset = data.get('preset', None)
    if preset is not None:
        base_path = os.environ.get("MONGO_ORCHESTRATION_HOME",
                                   os.path.dirname(__file__))
        path = os.path.join(base_path, 'configurations', cluster_type, preset)
        preset_data = {}
        with open(path, "r") as preset_file:
            preset_data = json.loads(preset_file.read())
        data = update(copy.deepcopy(preset_data), data)
    return data
