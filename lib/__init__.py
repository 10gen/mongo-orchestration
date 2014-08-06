#!/usr/bin/python
# coding=utf-8

from lib.hosts import Hosts
from lib.rs import RS
from lib.shards import Shards


def set_bin_path(bin_path=''):
    Hosts().set_settings(bin_path)
    RS().set_settings(bin_path)
    Shards().set_settings(bin_path)


def cleanup_storage():
    Shards().cleanup()
    RS().cleanup()
    Hosts().cleanup()
