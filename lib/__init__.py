#!/usr/bin/python
# coding=utf-8

from hosts import Hosts
from rs import RS
from shards import Shards


def set_storage(storage_path, bin_path=''):
    Hosts().set_settings(storage_path, bin_path)
    RS().set_settings(storage_path, bin_path)
    Shards().set_settings(storage_path, bin_path)


def cleanup_storage():
    Shards().cleanup()
    RS().cleanup()
    Hosts().cleanup()
