# coding=utf-8

import sys
sys.path.insert(0, '../')
import unittest
from modules.singleton import Singleton


class SingletonTestCase(unittest.TestCase):

    def test_singleton(self):
        a = Singleton()
        b = Singleton()
        self.assertEqual(id(a), id(b))


if __name__ == '__main__':
    unittest.main()
