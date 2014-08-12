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
        self.container = Container()
        self.container.set_settings()

    def tearDown(self):
        self.container.cleanup()

    def test_set_settings(self):
        path = os.path.join(os.getcwd(), 'bin')
        self.container.set_settings(path)
        self.assertEqual(path, self.container.bin_path)

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
