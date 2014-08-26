#!/usr/bin/python
# coding=utf-8

import sys

sys.path.insert(0, '../')

from lib.singleton import Singleton
from nose.plugins.attrib import attr
from tests import unittest


@attr('singleton')
@attr('test')
class SingletonTestCase(unittest.TestCase):

    def test_singleton(self):
        a = Singleton()
        b = Singleton()
        self.assertEqual(id(a), id(b))
        c = Singleton()
        self.assertEqual(id(c), id(b))


if __name__ == '__main__':
    unittest.main()
