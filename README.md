See the [wiki](mongo-orchestration/wiki) for documentation.

## Hosts command line

cmd_hosts.py - command line script used to test Hosts RestAPI

commands:
+ **create** - create new host
+ **delete** *host_id* - delete host
+ **info** *host_id* - get info about host
+ **list** - list of hosts
+ **start** *host_id* - start host
+ **stop** *host_id* - stop host
+ **restart** *host_id* - restart host

cmd_rs.py - command line script used to test RS RestAPI

supported operation for replica: *create*, *delete*, *list*, *info*

supported operation for members: *add*, *delete*(not master), *update*, *primary*, *info*

command format: `command rs_id  [member_id]  [params]`

**command** - command 
**rs_id** - replica id or replica index 
**member_id** - member id 
**params** - json string 

**Note: two space between args**

example: 

`shell: help` - print all commands

`shell: create [{}, {"rsParams": {"arbiterOnly": true}}, {"rsParams":{"hidden": true, "priority": 0}}, {}]`  
create new replica set: master+arbiter+hidden+secondary

`shell: list` - print all replica sets  

`shell: info 1` - print info about first replica set

`shell: members 1` - print info about members for replica set with index 1  

`shell: member_primary 1` - print info about primary node for replica set with index 1

`shell: member_update 1  3  {"rsParams": {"hidden": false, "priority": 3}}`
change parameters for member 3 in replica set 1

`shell: member_delete 1  1` - remove member from replica

`shell: member 1  2` - print info about member 2 in replica set 1
