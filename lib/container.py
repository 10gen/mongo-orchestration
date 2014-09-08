#!/usr/bin/python
# coding=utf-8

import logging

from lib.errors import MongoOrchestrationError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Container(object):
    """ Container is a dict-like collection for objects"""
    _storage = None
    _name = 'container'
    _obj_type = object

    def set_settings(self, releases=None, default_release=None):
        """set path to storage"""
        if (self._storage is None or
                getattr(self, 'releases', {}) != releases or
                getattr(self, 'default_release', '') != default_release):
            self._storage = {}
            self.releases = releases or {}
            self.default_release = default_release

    def bin_path(self, release=None):
        """Get the bin path for a particular release."""
        if release:
            for r in self.releases:
                if release in r:
                    return self.releases[r]
            raise MongoOrchestrationError("No such release '%s' in %r"
                                          % (release, self.releases))
        if self.default_release:
            return self.releases[self.default_release]
        return ''

    def __getitem__(self, key):
        return self._storage[key]

    def __setitem__(self, key, value):
        if isinstance(value, self._obj_type):
            self._storage[key] = value
        else:
            raise ValueError("Can only store objects of type %s, not %s"
                             % (self._obj_type, type(value)))

    def __delitem__(self, key):
        return self._storage.pop(key)

    def __del__(self):
        self.cleanup()

    def __contains__(self, item):
        return item in self._storage

    def __iter__(self):
        # Iterate over a copy of storage's keys
        return iter(list(self._storage))

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
