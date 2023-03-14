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

import os
import re
import time
import unittest
from unittest import SkipTest

from mongo_orchestration import set_releases
from mongo_orchestration.servers import Servers

PORT = int(os.environ.get('MO_PORT', '8889'))
HOSTNAME = os.environ.get('MO_HOST', 'localhost')
TEST_SUBJECT = (
    'C=US,ST=New York,L=New York City,O=MongoDB,OU=KernelUser,CN=client_revoked'
)
TEST_RELEASES = (
    {'default-release': os.environ.get('MONGOBIN', '')},
    'default-release')

# Set up the default mongo binaries to use from MONGOBIN.
set_releases(*TEST_RELEASES)

SSL_ENABLED = False
SERVER_VERSION = (2, 6)
__server_id = Servers().create(name='mongod', procParams={})
try:
    # Server version
    info = Servers().info(__server_id)['serverInfo']
    version_str = re.search(r'((\d+\.)+\d+)', info['version']).group(0)
    SERVER_VERSION = tuple(map(int, version_str.split('.')))
    # Do we have SSL support?
    SSL_ENABLED = bool(info.get('OpenSSLVersion'))
finally:
    Servers().cleanup()


class SSLTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not SSL_ENABLED:
            raise SkipTest("SSL is not enabled on this server.")


def certificate(cert_name):
    """Return the path to the PEM file with the given name."""
    return os.path.join(os.path.dirname(__file__), 'lib', cert_name)


def assert_eventually(condition, message=None, max_tries=60):
    for i in range(max_tries):
        if condition():
            break
        time.sleep(1)
    else:
        raise AssertionError(message or "Failed after %d attempts." % max_tries)
