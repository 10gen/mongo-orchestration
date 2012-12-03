#!/usr/bin/python
# coding=utf-8


class MongoOrchestrationError(Exception):
    """Base class for all mongo-orchestration exceptions.
    """


class HostsError(MongoOrchestrationError):
    """Base class for all Hosts exceptions.
    """


class ReplicaSetError(MongoOrchestrationError):
    """Base class for all ReplicaSet exceptions.
    """


class OperationFailure(MongoOrchestrationError):
    """Raised when an operation fails.
    """

    def __init__(self, error, code=None):
        self.code = code
        MongoOrchestrationError.__init__(self, error)


class TimeoutError(OperationFailure):
    """Raised when an operation times out.
    """
