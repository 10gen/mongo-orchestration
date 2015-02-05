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

import os
import operator
import sys

from bson import SON

sys.path.insert(0, '../')

from mongo_orchestration.container import Container
from mongo_orchestration.errors import MongoOrchestrationError
from tests import unittest


class ContainerTestCase(unittest.TestCase):
    def setUp(self):
        self.container = Container()
        self.container.set_settings()

    def tearDown(self):
        self.container.cleanup()

    def test_set_settings(self):
        default_release = 'old-release'
        releases = {default_release: os.path.join(os.getcwd(), 'bin')}
        orig_releases = self.container.releases
        orig_default_release = self.container.default_release
        try:
            self.container.set_settings(releases, default_release)
            self.assertEqual(releases, self.container.releases)
            self.assertEqual(default_release, self.container.default_release)
        finally:
            self.container.set_settings(orig_releases, orig_default_release)

    def test_bin_path(self):
        releases = SON([('20-release', '/path/to/20/release'),
                        ('24.9-release', '/path/to/24.9/release'),
                        ('24-release', '/path/to/24/release'),
                        ('26-release', '/path/to/26/release')])
        default_release = '26-release'
        self.container.set_settings(releases, default_release)
        self.assertRaises(MongoOrchestrationError,
                          self.container.bin_path, '27')
        self.assertEqual(self.container.bin_path('20'),
                         releases['20-release'])
        self.assertEqual(self.container.bin_path('24'),
                         releases['24.9-release'])
        self.assertEqual(self.container.bin_path(), releases[default_release])
        # Clear default release.
        self.container.set_settings(releases)
        self.assertEqual(self.container.bin_path(), releases['20-release'])
        # Clear all releases.
        self.container.set_settings({})
        self.assertEqual(self.container.bin_path(), '')

    def test_getitem(self):
        self.container['key'] = 'value'
        self.assertEqual('value', self.container['key'])
        self.assertRaises(KeyError, operator.getitem, self.container, 'error-key')

    def test_setitem(self):
        self.assertEqual(None, operator.setitem(self.container, 'key', 'value'))
        self.container._obj_type = int
        self.assertEqual(None, operator.setitem(self.container, 'key2', 15))
        self.assertRaises(ValueError, operator.setitem, self.container, 'key3', 'value')

    def test_delitem(self):
        self.assertEqual(0, len(self.container))
        self.container['key'] = 'value'
        self.assertEqual(1, len(self.container))
        self.assertEqual(None, operator.delitem(self.container, 'key'))
        self.assertEqual(0, len(self.container))

    def test_operations(self):
        self.assertEqual(0, len(self.container))
        keys = ('key1', 'key2', 'key3')
        values = ('value1', 'value2', 'value3')
        for key, value in zip(keys, values):
            self.container[key] = value
        self.assertEqual(len(keys), len(self.container))
        # test contains
        for key in keys:
            self.assertTrue(key in self.container)
        # test iteration
        for key in self.container:
            self.assertTrue(key in keys)
            self.assertTrue(self.container[key] in values)

        # test cleanup
        self.container.cleanup()
        self.assertEqual(0, len(self.container))

    def test_bool(self):
        self.assertEqual(False, bool(self.container))
        self.container['key'] = 'value'
        self.assertTrue(True, bool(self.container))

    def test_notimplemented(self):
        self.assertRaises(NotImplementedError, self.container.create)
        self.assertRaises(NotImplementedError, self.container.remove)
        self.assertRaises(NotImplementedError, self.container.info)

if __name__ == '__main__':
    unittest.main()
