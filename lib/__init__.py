#!/usr/bin/python
# coding=utf-8

from lib.servers import Servers
from lib.replica_sets import ReplicaSets
from lib.sharded_clusters import ShardedClusters


def set_bin_path(bin_path=''):
    Servers().set_settings(bin_path)
    ReplicaSets().set_settings(bin_path)
    ShardedClusters().set_settings(bin_path)


def cleanup_storage():
    ShardedClusters().cleanup()
    ReplicaSets().cleanup()
    Servers().cleanup()
