# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from lib.storage import Storage
import tempfile
import shutil
import operator


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(prefix="storage-test-")
        self.storage = Storage(self.path, 'test')

    def tearDown(self):
        if self.path:
            shutil.os.remove(self.path)

    def test_connect(self):
        self.assertTrue(self.storage.connect())

    def test_operation_set_get(self):
        self.storage['key'] = 'value'
        self.assertEqual(self.storage['key'], 'value')
        self.assertEqual(self.storage.get('key', ''), 'value')
        self.assertRaises(KeyError, operator.getitem, self.storage, 'non-existing-key')

    def test_operation_del(self):
        self.storage['key'] = 'value'
        del(self.storage['key'])
        self.assertRaises(KeyError, operator.getitem, self.storage, 'key')

    def test_operation_len(self):
        self.assertEqual(len(self.storage), 0)
        self.storage['key'] = 'value'
        self.assertEqual(len(self.storage), 1)
        self.storage['key2'] = 'value2'
        self.assertEqual(len(self.storage), 2)
        del(self.storage['key'])
        self.assertEqual(len(self.storage), 1)
        del(self.storage['key2'])
        self.assertEqual(len(self.storage), 0)

    def test_operation_contains(self):
        self.storage['key'] = 'value'
        self.assertTrue('key' in self.storage)
        self.assertFalse('key2' in self.storage)

    def test_operation_iter(self):
        sample = (('key', 'value'), ('key2', 'value2'), ('key3', 'value3'))
        for item in sample:
            operator.setitem(self.storage, item[0], item[1])

        for key in self.storage:
            self.assertTrue((key, self.storage[key]) in sample)

    def test_persistent(self):
        self.storage['key'] = 'value'
        self.assertEqual(self.storage['key'], 'value')
        del(self.storage)
        self.storage2 = Storage(self.path, 'test')
        self.assertEqual(self.storage2['key'], 'value')


if __name__ == '__main__':
    unittest.main()
