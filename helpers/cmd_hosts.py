#!/usr/bin/python
# coding=utf-8

import requests
import json
import cmd
import pprint


class CmdHosts(cmd.Cmd):
    """Simple command interpreter for testing Hosts Rest API"""
    hosts = list()
    api_url = 'http://localhost:8889/'

    def real_id(self, host_id):
        try:
            real_id = self.hosts[int(host_id) - 1]
            return real_id
        except (ValueError, IndexError):
            return host_id

    def print_result(self, r):
        print("========= Response data =========")
        obj = None
        try:
            obj = json.loads(r.text)
        except Exception:
            obj = r.text
        print("result code: {0}".format(r.status_code))
        if obj is not None:
            pprint.pprint(obj)
        print("=================================")

    def do_list(self, args):
        """list
        print list of hosts"""
        r = requests.get(self.api_url + "hosts")
        self.print_result(r)
        if r.status_code == 200:
            self.hosts = json.loads(r.text)
        for n, item in enumerate(self.hosts, 1):
            print("{0} {1}".format(n, item))

    def do_create(self, params):
        """create param
        create new host with json-string as param
        example: create {"name": "mongod"}"""
        r = requests.post(self.api_url + "hosts", data=params)
        self.print_result(r)
        if r.status_code == 200:
            self.hosts.append(json.loads(r.text)['id'])

    def do_info(self, host_id):
        """info id
        print host info"""
        r = requests.get(self.api_url + "hosts/" + self.real_id(host_id))
        self.print_result(r)

    def do_start(self, host_id):
        """start id
        start host by id, where id is host_id or item number in list command"""
        r = requests.put(self.api_url + "hosts/" + self.real_id(host_id) + "/start")
        print(r.status_code, r.text)

    def do_stop(self, host_id):
        """stop id
        stop host by id, where id is host_id or item number in list command"""
        r = requests.put(self.api_url + "hosts/" + self.real_id(host_id) + "/stop")
        self.print_result(r)

    def do_restart(self, host_id):
        """restart id
        restart host by id, where id is host_id or item number in list command"""
        r = requests.put(self.api_url + "hosts/" + self.real_id(host_id) + "/restart")
        self.print_result(r)

    def do_delete(self, host_id):
        """delete id
        delete host by id, where id is host_id or item number in list command"""
        r = requests.delete(self.api_url + "hosts/" + self.real_id(host_id))
        self.print_result(r)
        if r.status_code == 204:
            self.hosts.remove(self.real_id(host_id))

    def do_exit(self, line):
        """EXIT"""
        return True


if __name__ == '__main__':
    CmdHosts().cmdloop()
