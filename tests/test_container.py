#!/usr/bin/python
# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from lib.container import Container
import os
import tempfile
import time
import stat
import operator
from nose.plugins.attrib import attr


@attr('container')
@attr('test')
class ContainerTestCase(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(prefix="test-storage")
        self.container = Container()
        self.container.set_settings(self.path, None)

    def remove_path(self, path):
        onerror = lambda func, filepath, exc_info: (os.chmod(filepath, stat.S_IWUSR), func(filepath))
        # Disconnect SQlite from the database before deleting it.
        self.container._storage.disconnect()
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                time.sleep(2)
                onerror(os.remove, path, None)

    def tearDown(self):
        self.container.cleanup()
        self.remove_path(self.path)

    def test_set_settings(self):
        self.path = tempfile.mktemp(prefix="test-set-settings-")
        self.container.set_settings(self.path)
        self.assertEqual(self.path, self.container.pids_file)

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
