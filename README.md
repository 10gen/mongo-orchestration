See the [wiki](mongo-orchestration/wiki) for documentation.

**mongo-orchestration** - http server which provide rest api to management mongo's configurations

## Requires
[Python 2.7](http://www.python.org/download/)  
[psutil](https://code.google.com/p/psutil/downloads/list)

##Notes
+ tested on Ubuntu 12.04 and OS X 10.8.2
+ does not support Window
+ authorization does not implemented

## Command line scripts

### cmd_hosts.py - manage hosts

command format: `command host_id  [params]`  
**Note: two space between args**

commands:
+ **create {host params}** - create new host  
Example: `create {"name": "mongod"}`  

    ========= Response data =========
result code:  200
{u'id': u'e42ec4e4-8ba9-4200-9ba5-375b4c490cf8',
 u'procInfo': {u'alive': True,
               u'name': u'mongod',
               u'optfile': u'/tmp/mongo-kGmDvJ',
               u'params': {u'dbpath': u'/tmp/mongo-ehOPTO',
                           u'nojournal': u'true',
                           u'noprealloc': u'true',
                           u'oplogSize': 10,
                           u'port': 1035,
                           u'smallfiles': u'true'},
               u'pid': 31186},
 u'serverInfo': {u'bits': 64,
                 u'debug': False,
                 u'gitVersion': u'f5e83eae9cfbec7fb7a071321928f00d1b0c5207',
                 u'maxBsonObjectSize': 16777216,
                 u'ok': 1.0,
                 u'sysInfo': u'Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49',
                 u'version': u'2.2.0',
                 u'versionArray': [2, 2, 0, 0]},
 u'statuses': {u'locked': False, u'mongos': False, u'primary': True},
 u'uri': u'EPBYMINW0164T1:1035'}
=================================

+ **info [host-id]**  - show information about host
Example: `info 1`  
```
========= Response data =========
result code:  200
{u'id': u'e42ec4e4-8ba9-4200-9ba5-375b4c490cf8',
 u'procInfo': {u'alive': True,
               u'name': u'mongod',
               u'optfile': u'/tmp/mongo-kGmDvJ',
               u'params': {u'dbpath': u'/tmp/mongo-ehOPTO',
                           u'nojournal': u'true',
                           u'noprealloc': u'true',
                           u'oplogSize': 10,
                           u'port': 1035,
                           u'smallfiles': u'true'},
               u'pid': 31186},
 u'serverInfo': {u'bits': 64,
                 u'debug': False,
                 u'gitVersion': u'f5e83eae9cfbec7fb7a071321928f00d1b0c5207',
                 u'maxBsonObjectSize': 16777216,
                 u'ok': 1.0,
                 u'sysInfo': u'Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49',
                 u'version': u'2.2.0',
                 u'versionArray': [2, 2, 0, 0]},
 u'statuses': {u'locked': False, u'mongos': False, u'primary': True},
 u'uri': u'EPBYMINW0164T1:1035'}
=================================
```
+ **list** - show all hosts  
Example: `list`  
```
========= Response data =========
result code:  200
[u'e42ec4e4-8ba9-4200-9ba5-375b4c490cf8']
=================================
1 e42ec4e4-8ba9-4200-9ba5-375b4c490cf8
```
+ **stop [host_id]** - stop host  
Example: `stop 1`  
```
========= Response data =========
result code:  200
u''
=================================
```
+ **start [host_id]** - start host  
Example: `start 1`  
```
200
```
+ **restart [host_id]** - restart host  
Example: `restart 1`  
```
========= Response data =========
result code:  200
u''
=================================
```
+ **delete [host_id]** - delete host  
Example: `delete 1`  
```
========= Response data =========
result code:  204
u''
=================================
```


### cmd_rs.py - manage replica sets

command format: `command rs_id  [member_id]  [params]`  
**command** - command  
**rs_id** - replica id or replica index  
**member_id** - member id  
**params** - json string  

**Note: two space between args**

commands:
+ **help** - show help information
+ **create** - create new replica set  
Example: `create {"id":"default", "members": [{},{},{"rsParams": {"arbiterOnly":true}}, {"rsParams":{"hidden":true, "priority":0}}]}`  
```
========= Response data =========
result code:  200
{u'auth_key': None,
 u'id': u'default',
 u'members': [{u'_id': 0, u'host': u'EPBYMINW0164T1:1025'},
              {u'_id': 1, u'host': u'EPBYMINW0164T1:1026'},
              {u'_id': 2, u'host': u'EPBYMINW0164T1:1027'},
              {u'_id': 3, u'host': u'EPBYMINW0164T1:1028'}]}
=================================
[u'default']
```
+ **list** - show list of replicas , format: index replica-id  
Example: `list`  
```
========= Response data =========
result code:  200
[u'default']
=================================
1 default
```
+ **info [index or replica-id]** - show information about replica set  
Example: `info 1`  
```
========= Response data =========
result code:  200
{u'auth_key': None,
 u'id': u'default',
 u'members': [{u'_id': 0, u'host': u'EPBYMINW0164T1:1025'},
              {u'_id': 1, u'host': u'EPBYMINW0164T1:1026'},
              {u'_id': 2, u'host': u'EPBYMINW0164T1:1027'},
              {u'_id': 3, u'host': u'EPBYMINW0164T1:1028'}]}
=================================
```
+ **arbiters [index or replica-id]** - show list of arbiters hosts  
Example: `arbiters 1`  
```
========= Response data =========
result code:  200
[{u'_id': 2, u'host': u'EPBYMINW0164T1:1027'}]
=================================
```
+ **hidden [index or replica-id]** - show hidden hosts  
Example: `hidden 1`  
```
========= Response data =========
result code:  200
[{u'_id': 3, u'host': u'EPBYMINW0164T1:1028'}]
=================================
```
+ **secondaries** - show secondaries hosts  
Example: `secondaries [index or replica-id]`  
```
========= Response data =========
result code:  200
[{u'_id': 1, u'host': u'EPBYMINW0164T1:1026'},
 {u'_id': 3, u'host': u'EPBYMINW0164T1:1028'}]
=================================
```
+ **primary [index or replica-id]** - show information about primary host  
Example: `primary 1`  
```
========= Response data =========
result code:  200
{u'_id': 0,
 u'procInfo': {u'alive': True,
               u'name': u'mongod',
               u'optfile': u'/tmp/mongo-qiIHUz',
               u'params': {u'dbpath': u'/tmp/mongo-tgT1tD',
                           u'nojournal': u'true',
                           u'noprealloc': u'true',
                           u'oplogSize': 10,
                           u'port': 1025,
                           u'replSet': u'default',
                           u'smallfiles': u'true'},
               u'pid': 26806},
 u'rsInfo': {u'primary': True, u'secondary': False},
 u'statuses': {u'locked': False, u'mongos': False, u'primary': True},
 u'uri': u'EPBYMINW0164T1:1025'}
=================================
```
+ **stepdown [index or replica-id]** - stepdown primary host  
Example: `stepdown 1`  
```
========= Response data =========
result code:  200
u''
=================================
```
+ **members** - show all replicaset's members  
Example: `members [index or replica-id]`  
```
========= Response data =========
result code:  200
[{u'_id': 0, u'host': u'EPBYMINW0164T1:1025'},
 {u'_id': 1, u'host': u'EPBYMINW0164T1:1026'},
 {u'_id': 2, u'host': u'EPBYMINW0164T1:1027'},
 {u'_id': 3, u'host': u'EPBYMINW0164T1:1028'}]
=================================
```
+ **member_add [index or replica-id]  {member config}** - add new member to replica set  
Example: `member_add 1  {"rsParams": {"hidden": true, "priority": 0}}  
```
========= Response data =========
result code:  200
[{u'_id': 0, u'host': u'EPBYMINW0164T1:1025'},
 {u'_id': 1, u'host': u'EPBYMINW0164T1:1026'},
 {u'_id': 2, u'host': u'EPBYMINW0164T1:1027'},
 {u'_id': 3, u'host': u'EPBYMINW0164T1:1028'},
 {u'_id': 4, u'host': u'EPBYMINW0164T1:1030'}]
=================================
```
+ **member_info [index or replica-id]  [member-id]** - show information about member  
Example: `member_info 1  4`  
```
========= Response data =========
result code:  200
{u'_id': 4,
 u'procInfo': {u'alive': True,
               u'name': u'mongod',
               u'optfile': u'/tmp/mongo-XDk4wy',
               u'params': {u'dbpath': u'/tmp/mongo-1KL3aQ',
                           u'nojournal': u'true',
                           u'noprealloc': u'true',
                           u'oplogSize': 10,
                           u'port': 1030,
                           u'replSet': u'default',
                           u'smallfiles': u'true'},
               u'pid': 28377},
 u'rsInfo': {u'hidden': True, u'primary': False, u'secondary': True},
 u'statuses': {u'locked': False, u'mongos': False, u'primary': False},
 u'uri': u'EPBYMINW0164T1:1030'}
=================================
```
+ **member_update [index or replica-id]  [member-id]** - update member params  
Example: `member_update 1  4  {"rsParams": {"hidden":false, "priority": 3}}`  
```
========= Response data =========
result code:  200
{u'_id': 4,
 u'procInfo': {u'alive': True,
               u'name': u'mongod',
               u'optfile': u'/tmp/mongo-XDk4wy',
               u'params': {u'dbpath': u'/tmp/mongo-1KL3aQ',
                           u'nojournal': u'true',
                           u'noprealloc': u'true',
                           u'oplogSize': 10,
                           u'port': 1030,
                           u'replSet': u'default',
                           u'smallfiles': u'true'},
               u'pid': 28377},
 u'rsInfo': {u'primary': True, u'secondary': False},
 u'statuses': {u'locked': False, u'mongos': False, u'primary': True},
 u'uri': u'EPBYMINW0164T1:1030'}
=================================
```
+ **member_command [index or replica-id]  [member-id]  [command]** - start/stop/restart host  
Example: `member_command 1  4  stop`  
```
========= Response data =========
result code:  200
u''
=================================

```
+ **member_delete [index or replcia-id]  [member-id]** - remove host from replica set  
Example: `member_delete 1  4`  
```
========= Response data =========
result code:  200
True
=================================
```
+ **delete [index or replica-id]** - remove replica set  
Example: `delete 1`  
```
========= Response data =========
result code:  204
u''
=================================
```