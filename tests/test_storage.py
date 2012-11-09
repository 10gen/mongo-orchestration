# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from lib.storage import Storage
import tempfile
import shutil


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(prefix="storage-test-")
        self.storage = Storage(self.path, 'test')

    def tearDown(self):
        if self.path:
            shutil.os.remove(self.path)

    def test_persistent(self):
        self.storage['key'] = 'value'
        self.assertEqual(self.storage['key'], 'value')
        del(self.storage)
        self.storage2 = Storage(self.path, 'test')
        self.assertEqual(self.storage2['key'], 'value')

    def test_storage(self):
        self.storage['key'] = 'value'
        self.storage['key2'] = 'value2'
        self.assertEqual(self.storage['key'], 'value')
        self.assertEqual(self.storage['key2'], 'value2')
        self.assertEqual(len(self.storage), 2)
        self.assertTrue('key' in self.storage)
        self.storage.pop('key')
        self.assertFalse('key' in self.storage)
        self.assertEqual(len(self.storage), 1)


if __name__ == '__main__':
    unittest.main()
