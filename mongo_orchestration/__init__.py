#!/usr/bin/python
# coding=utf-8
# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from mongo_orchestration.servers import Servers
from mongo_orchestration.replica_sets import ReplicaSets
from mongo_orchestration.sharded_clusters import ShardedClusters

__version__ = '0.4.2'


def set_releases(releases=None, default_release=None):
    Servers().set_settings(releases, default_release)
    ReplicaSets().set_settings(releases, default_release)
    ShardedClusters().set_settings(releases, default_release)


def cleanup_storage(*args):
    """Clean up processes after SIGTERM or SIGINT is received."""
    ShardedClusters().cleanup()
    ReplicaSets().cleanup()
    Servers().cleanup()
    sys.exit(0)
