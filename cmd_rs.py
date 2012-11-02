# coding=utf-8

import requests
import json
import cmd
import pprint


class CmdRS(cmd.Cmd):
    """Simple command interpreter for testing Replica Set Rest API"""
    rs = list()
    api_url = 'http://localhost:8889/'

    def real_id(self, rs_id):
        try:
            real_id = self.rs[int(rs_id) - 1]
            return real_id
        except (ValueError, IndexError):
            return rs_id

    def print_result(self, r):
        print "========= Response data ========="
        obj = None
        try:
            obj = json.loads(r.text)
        except Exception:
            obj = r.text
        print "result code: ", r.status_code
        if obj is not None:
            pprint.pprint(obj)
        print "================================="

    def do_list(self, args):
        """list
        print list of rs"""
        r = requests.get(self.api_url + "rs")
        self.print_result(r)
        if r.status_code == 200:
            self.rs = json.loads(r.text)
        for n, item in enumerate(self.rs, 1):
            print n, item

    def do_create(self, params):
        """create param
        create replica set with json-string as param
        example: create [{}, {}, {}]"""
        r = requests.post(self.api_url + "rs", data=params)
        self.print_result(r)
        if r.status_code == 200:
            self.rs.append(json.loads(r.text)['id'])
            print self.rs

    def do_info(self, rs_id):
        """info id
        print replica set info"""
        r = requests.get(self.api_url + "rs/" + self.real_id(rs_id))
        self.print_result(r)

    def do_delete(self, rs_id):
        """delete id
        delete replica set by id, where id is rs_id or item number in list command"""
        r = requests.delete(self.api_url + "rs/" + self.real_id(rs_id))
        self.print_result(r)
        if r.status_code == 204:
            self.rs.remove(self.real_id(rs_id))

    def do_member_add(self, args):
        args = args.split('  ')
        rs_id = args[0]
        params = args[1]
        url = "{url}rs/{rs_id}/members".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.post(url, data=params)
        self.print_result(r)

    def do_member_info(self, args):
        args = args.split('  ')
        rs_id = args[0]
        member_id = args[1]
        url = "{url}rs/{rs_id}/members/{member_id}".format(url=self.api_url, rs_id=self.real_id(rs_id), member_id=member_id)
        r = requests.get(url)
        self.print_result(r)

    def do_members(self, rs_id):
        url = "{url}rs/{rs_id}/members".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.get(url)
        self.print_result(r)

    def do_member_update(self, args):
        args = args.split('  ')
        rs_id = args[0]
        member_id = args[1]
        params = args[2]
        url = "{url}rs/{rs_id}/members/{member_id}".format(url=self.api_url, rs_id=self.real_id(rs_id), member_id=member_id)
        r = requests.put(url, params)
        self.print_result(r)

    def do_member_delete(self, args):
        args = args.split('  ')
        rs_id = args[0]
        member_id = args[1]
        url = "{url}rs/{rs_id}/members/{member_id}".format(url=self.api_url, rs_id=self.real_id(rs_id), member_id=member_id)
        r = requests.delete(url)
        self.print_result(r)

    def do_primary(self, rs_id):
        url = "{url}rs/{rs_id}/primary".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.get(url)
        self.print_result(r)

    def do_member_command(self, args):
        args = args.split('  ')
        rs_id = args[0]
        member_id = args[1]
        command = args[2]
        url = "{url}rs/{rs_id}/members/{member_id}/{command}".format(url=self.api_url, rs_id=self.real_id(rs_id), member_id=member_id, command=command)
        r = requests.put(url)
        self.print_result(r)

    def do_stepdown(self, args):
        args = map(lambda item: item.strip(' '), args.split('  '))
        rs_id = args[0]
        params = "{}"
        if len(args) > 1:
            params = args[1]
        url = "{url}rs/{rs_id}/primary/stepdown".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.put(url, params)
        self.print_result(r)

    def do_secondaries(self, rs_id):
        url = "{url}rs/{rs_id}/secondaries".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.get(url)
        self.print_result(r)

    def do_arbiters(self, rs_id):
        url = "{url}rs/{rs_id}/arbiters".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.get(url)
        self.print_result(r)

    def do_hidden(self, rs_id):
        url = "{url}rs/{rs_id}/hidden".format(url=self.api_url, rs_id=self.real_id(rs_id))
        r = requests.get(url)
        self.print_result(r)

    def do_exit(self, line):
        """EXIT"""
        return True


if __name__ == '__main__':
    CmdRS().cmdloop()
