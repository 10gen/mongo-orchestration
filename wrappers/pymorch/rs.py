#!/usr/bin/python
# coding=utf-8
from hosts import Host
from common import request


class ReplMember(Host):

    base_url = "rs"

    def __init__(self, repl_id, member_id, host_id, api_url='http://localhost:8889'):
        super(ReplMember, self).__init__(host_id, api_url)
        self.__repl_id = repl_id
        self.__member_id = member_id

    @property
    def id(self):
        return self.__member_id

    @property
    def info(self):
        url = "{api_url}/{base_url}/{config_id}/members/{member_id}".format(api_url=self.api_url,
                                                                            base_url=self.base_url,
                                                                            config_id=self.__repl_id,
                                                                            member_id=str(self.id))
        return request('get', url)

    def update(self, params):
        url = "{api_url}/{base_url}/{config_id}/members/{member_id}".format(api_url=self.api_url,
                                                                            base_url=self.base_url,
                                                                            config_id=self.__repl_id,
                                                                            member_id=str(self.id))
        return request('put', url, data=params)

    @property
    def is_hidden(self):
        return self.info.get('rsInfo', {}).get('hidden', False)

    @property
    def is_arbiter(self):
        return self.info.get('rsInfo', {}).get('arbiterOnly', False)

    @property
    def is_secondary(self):
        return self.info.get('rsInfo', {}).get('secondary', False)


class ReplicaSet(object):
    """wrap rest api for replicaset objects"""

    base_url = "rs"

    def __init__(self, repl_id, api_url='http://localhost:8889'):
        self.__id = repl_id
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
        return [ReplMember(self.id, member['_id'], member['host_id'], self.api_url)
                for member in request('get', url)]

    def member_remove(self, member_id):
        url = "{api_url}/{base_url}/{config_id}/members/{member_id}".format(api_url=self.api_url,
                                                                            base_url=self.base_url,
                                                                            config_id=self.id,
                                                                            member_id=member_id)
        return request('delete', url)

    def member_add(self, member_id, params):
        url = "{api_url}/{base_url}/{config_id}/members".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)
        member = request('post', url, data=params)
        return ReplMember(self.id, member['_id'], member['host_id'], self.api_url)

    def primary(self):
        url = "{api_url}/{base_url}/{config_id}/primary".format(api_url=self.api_url,
                                                                base_url=self.base_url,
                                                                config_id=self.id)

        member = request('get', url)
        return ReplMember(self.id, member['_id'], member['host_id'], self.api_url)

    def stepdown(self):
        url = "{api_url}/{base_url}/{config_id}/primary/stepdown".format(api_url=self.api_url,
                                                                         base_url=self.base_url,
                                                                         config_id=self.id)

        return request('put', url)

    def secondaries(self):
        url = "{api_url}/{base_url}/{config_id}/secondaries".format(api_url=self.api_url,
                                                                    base_url=self.base_url,
                                                                    config_id=self.id)
        return [ReplMember(self.id, member['_id'], member['host_id']) for member in request('get', url)]

    def arbiters(self):
        url = "{api_url}/{base_url}/{config_id}/arbiters".format(api_url=self.api_url,
                                                                 base_url=self.base_url,
                                                                 config_id=self.id)
        return [ReplMember(self.id, member['_id'], member['host_id']) for member in request('get', url)]

    def hidden(self):
        url = "{api_url}/{base_url}/{config_id}/hidden".format(api_url=self.api_url,
                                                               base_url=self.base_url,
                                                               config_id=self.id)
        return [ReplMember(self.id, member['_id'], member['host_id']) for member in request('get', url)]


class RSMeta(type):
    def __len__(cls):
        return RS.__len__()

    def __iter__(cls):
        return RS.__iter__()

    def __contains__(cls, host):
        return RS.__contains__(host)


class RS(object):
    """wrap rest api for RS"""

    __metaclass__ = RSMeta

    api_url = 'http://localhost:8889'
    base_url = 'rs'

    @staticmethod
    def create(params):
        url = "{api_url}/{base_url}".format(api_url=RS.api_url,
                                            base_url=RS.base_url)

        return ReplicaSet(request('post', url, data=params)['id'], RS.api_url)

    @staticmethod
    def _ids():
        url = "{api_url}/{base_url}".format(api_url=RS.api_url,
                                            base_url=RS.base_url)
        return request('get', url)

    @staticmethod
    def __iter__():
        for _id in RS._ids():
            yield ReplicaSet(_id)

    @staticmethod
    def __len__():
        return len(RS._ids())

    @staticmethod
    def __contains__(repl):
        return repl.id in RS._ids()

    @staticmethod
    def remove(repl):
        url = "{api_url}/{base_url}/{config_id}".format(api_url=RS.api_url,
                                                        base_url=RS.base_url,
                                                        config_id=repl.id)
        return request('delete', url)

    @staticmethod
    def cleanup():
        for repl in RS:
            RS.remove(repl)
