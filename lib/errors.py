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


class MongoOrchestrationError(Exception):
    """Base class for all mongo-orchestration exceptions."""


class RequestError(MongoOrchestrationError):
    """Raised when a bad request is made to the web interface."""


class ServersError(MongoOrchestrationError):
    """Base class for all Server exceptions."""


class ReplicaSetError(MongoOrchestrationError):
    """Base class for all ReplicaSet exceptions."""


class ShardedClusterError(MongoOrchestrationError):
    """Base class for all ShardedCluster exceptions."""


class OperationFailure(MongoOrchestrationError):
    """Raised when an operation fails."""

    def __init__(self, error, code=None):
        self.code = code  # pragma: no cover
        MongoOrchestrationError.__init__(self, error)  # pragma: no cover


class TimeoutError(OperationFailure):
    """Raised when an operation times out."""
