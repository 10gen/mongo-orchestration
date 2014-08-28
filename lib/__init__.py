#!/usr/bin/python
# coding=utf-8

from lib.servers import Servers
from lib.replica_sets import ReplicaSets
from lib.sharded_clusters import ShardedClusters


def set_releases(releases=None, default_release=None):
    Servers().set_settings(releases, default_release)
    ReplicaSets().set_settings(releases, default_release)
    ShardedClusters().set_settings(releases, default_release)


def cleanup_storage():
    ShardedClusters().cleanup()
    ReplicaSets().cleanup()
    Servers().cleanup()
