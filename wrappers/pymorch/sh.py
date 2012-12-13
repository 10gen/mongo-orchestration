#!/usr/bin/python
# coding=utf-8
from hosts import Host
from rs import ReplicaSet
from common import request


class ShardMember(object):

    base_url = "sh"

    def __init__(self, cluster_id, member_id, _id, api_url='http://localhost:8889'):
        self.api_url = api_url
        self.__cluster_id = cluster_id
        self.__member_id = member_id
        self.__origin_id = _id

    @property
    def id(self):
        return str(self.__member_id)

    @property
    def info(self):
        url = "{api_url}/{base_url}/{config_id}/members/{member_id}".format(api_url=self.api_url,
                                                                            base_url=self.base_url,
                                                                            config_id=self.__cluster_id,
                                                                            member_id=self.id)
        return request('get', url)

    @property
    def origin(self):
        if self.is_host:
            return Host(self.__origin_id, self.api_url)

        if self.is_replica:
            return ReplicaSet(self.__origin_id, self.api_url)

    @property
    def is_host(self):
        return self.info.get('isHost', True)

    @property
    def is_replica(self):
        return self.info.get('isReplicaSet', True)


class Shard(object):
    """wrap rest api for replicaset objects"""

    base_url = "sh"

    def __init__(self, sh_id, api_url='http://localhost:8889'):
        self.__id = sh_id
        self.api_url = api_url

    @property
    def id(self):
        return self.__id

    @property
    def info(self):
        url = "{api_url}/{base_url}/{config_id}".format(api_url=self.api_url,
                                                        base_url=self.base_url,
                                                        config_id=self.id)
        return request('get', url)

    def members(self):
        url = "{api_url}/{base_url}/{config_id}/members".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)
        return [ShardMember(self.id, member['id'], member['_id']) for member in request('get', url)]

    def member_remove(self, member_id):
        url = "{api_url}/{base_url}/{config_id}/members/{member_id}".format(api_url=self.api_url,
                                                                            base_url=self.base_url,
                                                                            config_id=self.id,
                                                                            member_id=member_id)
        return request('delete', url)

    def member_add(self, params):
        url = "{api_url}/{base_url}/{config_id}/members".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)
        member = request('post', url, data=params)
        return ShardMember(self.id, member['id'], member['_id'])

    def configservers(self):
        url = "{api_url}/{base_url}/{config_id}/configservers".format(api_url=self.api_url,
                                                                      base_url=self.base_url,
                                                                      config_id=self.id)
        return [Host(member['id']) for member in request('get', url)]

    def routers(self):
        url = "{api_url}/{base_url}/{config_id}/routers".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)
        return [Host(member['id']) for member in request('get', url)]

    def routerr_add(self, params):
        url = "{api_url}/{base_url}/{config_id}/routers".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)
        return request('post', url, data=params)


class SHMeta(type):
    def __len__(cls):
        return SH.__len__()

    def __iter__(cls):
        return SH.__iter__()

    def __contains__(cls, sh):
        return SH.__contains__(sh)


class SH(object):
    """wrap rest api for RS"""

    __metaclass__ = SHMeta

    api_url = 'http://localhost:8889'
    base_url = 'sh'

    @staticmethod
    def create(params):
        url = "{api_url}/{base_url}".format(api_url=SH.api_url,
                                            base_url=SH.base_url)
        return Shard(request('post', url, data=params)['id'], SH.api_url)

    @staticmethod
    def _ids():
        url = "{api_url}/{base_url}".format(api_url=SH.api_url,
                                            base_url=SH.base_url)
        return request('get', url)

    @staticmethod
    def __iter__():
        for _id in SH._ids():
            yield Shard(_id)

    @staticmethod
    def __len__():
        return len(SH._ids())

    @staticmethod
    def __contains__(sh):
        return sh.id in SH._ids()

    @staticmethod
    def remove(sh):
        url = "{api_url}/{base_url}/{config_id}".format(api_url=SH.api_url,
                                                        base_url=SH.base_url,
                                                        config_id=sh.id)
        return request('delete', url)

    @staticmethod
    def cleanup():
        for sh in SH:
            SH.remove(sh)
