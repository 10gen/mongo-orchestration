#!/usr/bin/python
# coding=utf-8


class MongoOrchestrationError(Exception):
    """Base class for all mongo-orchestration exceptions."""


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
