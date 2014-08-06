#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from storage import Storage


class Container(object):
    """ Container is a dict-like collection for objects"""
    _storage = None
    _name = 'container'
    _obj_type = object

    def set_settings(self, bin_path=None):
        """set path to storage"""
        if self._storage is None or getattr(self, 'bin_path', '') != bin_path:
            self._storage = {}
            self.bin_path = bin_path or ''

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        if isinstance(value, self._obj_type):
            self._storage[key] = value
        else:
            raise ValueError

    def __delitem__(self, key):
        return self._storage.pop(key)

    def __contains__(self, item):
        return item in self._storage

    def __iter__(self):
        # Iterate over a copy of storage's keys
        return iter(self._storage.keys())

    def __len__(self):
        return len(self._storage)

    def __nonzero__(self):
        return bool(len(self))

    def __bool__(self):
        # Python 3 compatibility
        return self.__nonzero__()  # pragma: no cover

    def cleanup(self):
        self._storage.clear()

    def create(self):
        raise NotImplementedError("Please Implement this method")

    def remove(self):
        raise NotImplementedError("Please Implement this method")

    def info(self):
        raise NotImplementedError("Please Implement this method")
