#!/usr/bin/python
#!/usr/bin/python
# coding=utf-8

import requests
import json
import cmd
import pprint


class CmdSH(cmd.Cmd):
    """Simple command interpreter for testing shard cluster Rest API"""
    sh = list()
    api_url = 'http://localhost:8889/'

    def real_id(self, sh_id):
        try:
            real_id = self.sh[int(sh_id) - 1]
            return real_id
        except (ValueError, IndexError):
            return sh_id

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
        print list of sh"""
        r = requests.get(self.api_url + "sh")
        self.print_result(r)
        if r.status_code == 200:
            self.sh = json.loads(r.text)
        for n, item in enumerate(self.sh, 1):
            print("{0} {1}".format(n, item))

    def do_create(self, params):
        """create param
        create shard cluster with json-string as param
        example: create [{}, {}, {}]"""
        r = requests.post(self.api_url + "sh", data=params)
        self.print_result(r)
        if r.status_code == 200:
            self.sh.append(json.loads(r.text)['id'])
            print(self.sh)

    def do_info(self, sh_id):
        """info id
        print shard cluster info"""
        r = requests.get(self.api_url + "sh/" + self.real_id(sh_id))
        self.print_result(r)

    def do_delete(self, sh_id):
        """delete id
        delete shard cluster by id, where id is sh_id or item number in list command"""
        r = requests.delete(self.api_url + "sh/" + self.real_id(sh_id))
        self.print_result(r)
        if r.status_code == 204:
            self.sh.remove(self.real_id(sh_id))

    def do_member_add(self, args):
        args = args.split('  ')
        sh_id = args[0]
        params = args[1]
        url = "{url}sh/{sh_id}/members".format(url=self.api_url, sh_id=self.real_id(sh_id))
        r = requests.post(url, data=params)
        self.print_result(r)

    def do_member_info(self, args):
        args = args.split('  ')
        sh_id = args[0]
        member_id = args[1]
        url = "{url}sh/{sh_id}/members/{member_id}".format(url=self.api_url, sh_id=self.real_id(sh_id), member_id=member_id)
        r = requests.get(url)
        self.print_result(r)

    def do_members(self, sh_id):
        url = "{url}sh/{sh_id}/members".format(url=self.api_url, sh_id=self.real_id(sh_id))
        r = requests.get(url)
        self.print_result(r)

    def do_member_delete(self, args):
        args = args.split('  ')
        sh_id = args[0]
        member_id = args[1]
        url = "{url}sh/{sh_id}/members/{member_id}".format(url=self.api_url, sh_id=self.real_id(sh_id), member_id=member_id)
        r = requests.delete(url)
        self.print_result(r)

    def do_configsvrs(self, sh_id):
        url = "{url}sh/{sh_id}/configsvrs".format(
            url=self.api_url, sh_id=self.real_id(sh_id))
        r = requests.get(url)
        self.print_result(r)

    def do_routers(self, sh_id):
        url = "{url}sh/{sh_id}/routers".format(url=self.api_url, sh_id=self.real_id(sh_id))
        r = requests.get(url)
        self.print_result(r)

    def do_router_add(self, args):
        args = args.split('  ')
        sh_id = args[0]
        params = args[1]
        url = "{url}sh/{sh_id}/routers".format(url=self.api_url, sh_id=self.real_id(sh_id))
        r = requests.post(url, data=params)
        self.print_result(r)

    def do_router_delete(self, args):
        args = args.split('  ')
        sh_id = args[0]
        router_id = args[1]
        url = "{url}sh/{sh_id}/routers/{router_id}".format(url=self.api_url, sh_id=self.real_id(sh_id), router_id=router_id)
        r = requests.delete(url)
        self.print_result(r)

    def do_exit(self, line):
        """EXIT"""
        return True


if __name__ == '__main__':
    CmdSH().cmdloop()
