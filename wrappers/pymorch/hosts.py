#!/usr/bin/python
# coding=utf-8
from common import request


class Host(object):
    """wrap rest api for host object"""
    api_url = 'http://localhost:8889'
    base_url = 'hosts'

    def __init__(self, host_id, api_url='http://localhost:8889'):
        self.__host_id = host_id
        self.api_url = api_url

    @property
    def id(self):
        return self.__host_id

    def start(self):
        url = "{api_url}/hosts/{config_id}/start".format(api_url=self.api_url,
                                                         base_url=self.base_url,
                                                         config_id=self.__host_id)
        return request('put', url)

    def stop(self):
        url = "{api_url}/hosts/{config_id}/stop".format(api_url=self.api_url,
                                                        base_url=self.base_url,
                                                        config_id=self.__host_id)
        return request('put', url)

    def restart(self):
        url = "{api_url}/hosts/{config_id}/restart".format(api_url=self.api_url,
                                                           base_url=self.base_url,
                                                           config_id=self.__host_id)
        return request('put', url)

    @property
    def info(self):
        url = "{api_url}/hosts/{config_id}".format(api_url=self.api_url,
                                                   base_url=self.base_url,
                                                   config_id=self.__host_id)
        return request('get', url)

    @property
    def is_alive(self):
        return self.info['procInfo'].get('alive', False)

    @property
    def is_mongos(self):
        return self.info['statuses'].get('mongos', False)

    @property
    def is_primary(self):
        return self.info['statuses'].get('primary', False)

    @property
    def uri(self):
        return self.info['uri']


class HostsMeta(type):
    def __len__(cls):
        return Hosts.__len__()

    def __iter__(cls):
        return Hosts.__iter__()

    def __contains__(cls, host):
        return Hosts.__contains__(host)


class Hosts(object):
    """wrap rest api for hosts"""

    __metaclass__ = HostsMeta

    api_url = 'http://localhost:8889'
    base_url = 'hosts'

    @staticmethod
    def create(params):
        url = "{api_url}/hosts".format(api_url=Hosts.api_url,
                                       base_url=Hosts.base_url)

        return Host(request('post', url, data=params)['id'], Hosts.api_url)

    @staticmethod
    def _ids():
        url = "{api_url}/hosts".format(api_url=Hosts.api_url,
                                       base_url=Hosts.base_url)

        return request('get', url)

    @staticmethod
    def __iter__():
        for _id in Hosts._ids():
            yield Host(_id)

    @staticmethod
    def __len__():
        return len(Hosts._ids())

    @staticmethod
    def __contains__(host):
        return host.id in Hosts._ids()

    @staticmethod
    def remove(host):
        url = "{api_url}/hosts/{config_id}".format(api_url=Hosts.api_url,
                                                   base_url=Hosts.base_url,
                                                   config_id=host.id)

        return request('delete', url)

    @staticmethod
    def cleanup():
        for host in Hosts:
            Hosts.remove(host)
