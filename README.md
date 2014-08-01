[![Build Status](https://jenkins.10gen.com/job/mongo-orchestration/badge/icon)](https://jenkins.10gen.com/job/mongo-orchestration/)


See the [wiki](https://github.com/mongodb/mongo-orchestration/wiki) for documentation.

**mongo-orchestration** - http server which provide rest api to management mongo's configurations

##Features

Supported configurations: **Host**, **ReplicaSet**, **ShardCluster**  

###Hosts
+ **setup** - setup host using options
+ **control** - start/stop/restart instance
+ **information** - return information about host

###ReplicaSet
+ **setup** - setup replica set using configuration structure
+ **configure** - add/remove members
+ **control** - start/stop/restart members
+ **information** - return information about replicaset
+ **authentication**  - support authentication by keyFile


###Shard Cluster
+ **setup** - setup shard cluster using configuration structure
+ **configure** - add/remove members
+ **information** - return information about replicaset
+ **authentication**  - support authentication by keyFile

##Requires
- [Python 2.7](http://www.python.org/download/)  
- [requests](http://docs.python-requests.org/en/latest/user/install/#install)
- [PyMongo 2.5.2](http://api.mongodb.org/python/2.5.2/)

##Installing

###Ubuntu
`sudo apt-get install python-pip && sudo pip install pymongo\>=2.7.2 requests\>=0.12`

###OSX

##Usage
`python server.py [-h] [-f CONFIG] [-e ENV] [--no-fork] [-p PORT] {start,stop,restart}`  
  
Arguments:  
+ **-h** - show help info
+ **-f** - path to config file, default: mongo-orchestration.config  
+ **-e** - release name from config file, 'default' by default  
+ **--no-fork** - don't start as service  
+ **-p** - port number, 8889 by default  
+ **start/stop/restart**: server's command  

###Examples
`python server.py start` - starts as service on 8889 port  
`python server.py stop` - stop server  
`python server.py -e stable-release -p 8888 --no-fork start` - starts on 8888 port using stable-release. Stops by *Ctrl+C*  


##Notes
+ tested on Ubuntu 12.04 and OS X 10.8.2
+ does not support Windows

## Predefined configurations
There is a set of predefined configurations in repository. They can be started with '#' script from root folder. 

To start a single node without ssl or auth:
```bash
./# configurations/hosts/clean.json 
```

To start a single node with ssl, but no auth:
```bash
./# configurations/hosts/ssl.json 
```

To start a replica set with ssl and auth:
```bash
./# configurations/rs/ssl_auth.json 
```

To start a sharded cluster with auth:
```bash
./# configurations/sh/auth.json 
```


## Command line scripts
  
+ **cmd_hosts.py** - manage hosts
+ **cmd_rs.py**    - manage replica sets
+ **cmd_sh.py**    - manage shard clusters

### cmd_hosts.py - manage hosts

command format: `command host_id  [params]`  
**Note: two space between args**

commands:
+ **create {host params}** - create new host  
Example: `create {"name": "mongod"}`  

```javascript
========= Response data =========
result code:  200
{'id': 'e42ec4e4-8ba9-4200-9ba5-375b4c490cf8',
 'procInfo': {'alive': True,
               'name': 'mongod',
               'optfile': '/tmp/mongo-kGmDvJ',
               'params': {'dbpath': '/tmp/mongo-ehOPTO',
                           'nojournal': 'true',
                           'noprealloc': 'true',
                           'oplogSize': 10,
                           'port': 1035,
                           'smallfiles': 'true'},
               'pid': 31186},
 'serverInfo': {'bits': 64,
                 'debug': False,
                 'gitVersion': 'f5e83eae9cfbec7fb7a071321928f00d1b0c5207',
                 'maxBsonObjectSize': 16777216,
                 'ok': 1.0,
                 'sysInfo': 'Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49',
                 'version': '2.2.0',
                 'versionArray': [2, 2, 0, 0]},
 'statuses': {'locked': False, 'mongos': False, 'primary': True},
 'uri': 'EPBYMINW0164T1:1035'}
=================================
```
+ **info [host-id]**  - show information about host  
Example: `info 1`  

```javascript
========= Response data =========
result code:  200
{'id': 'e42ec4e4-8ba9-4200-9ba5-375b4c490cf8',
 'procInfo': {'alive': True,
               'name': 'mongod',
               'optfile': '/tmp/mongo-kGmDvJ',
               'params': {'dbpath': '/tmp/mongo-ehOPTO',
                           'nojournal': 'true',
                           'noprealloc': 'true',
                           'oplogSize': 10,
                           'port': 1035,
                           'smallfiles': 'true'},
               'pid': 31186},
 'serverInfo': {'bits': 64,
                 'debug': False,
                 'gitVersion': 'f5e83eae9cfbec7fb7a071321928f00d1b0c5207',
                 'maxBsonObjectSize': 16777216,
                 'ok': 1.0,
                 'sysInfo': 'Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49',
                 'version': '2.2.0',
                 'versionArray': [2, 2, 0, 0]},
 'statuses': {'locked': False, 'mongos': False, 'primary': True},
 'uri': 'EPBYMINW0164T1:1035'}
=================================
```

+ **list** - show all hosts  
Example: `list`  

```javascript
========= Response data =========
result code:  200
['e42ec4e4-8ba9-4200-9ba5-375b4c490cf8']
=================================
1 e42ec4e4-8ba9-4200-9ba5-375b4c490cf8
```

+ **stop [host_id]** - stop host  
Example: `stop 1`  

```javascript
========= Response data =========
result code:  200
''
=================================
```

+ **start [host_id]** - start host  
Example: `start 1`  

```javascript
200
```

+ **restart [host_id]** - restart host  
Example: `javascriptrestart 1`  

```
========= Response data =========
result code:  200
''
=================================
```

+ **delete [host_id]** - delete host  
Example: `delete 1`  

```javascript
========= Response data =========
result code:  204
''
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

```javascript
========= Response data =========
result code:  200
{'auth_key': None,
 'id': 'default',
 'members': [{'_id': 0, 'host': 'EPBYMINW0164T1:1025'},
              {'_id': 1, 'host': 'EPBYMINW0164T1:1026'},
              {'_id': 2, 'host': 'EPBYMINW0164T1:1027'},
              {'_id': 3, 'host': 'EPBYMINW0164T1:1028'}]}
=================================
['default']
```

+ **list** - show list of replicas , format: index replica-id  
Example: `list`  

```javascript
========= Response data =========
result code:  200
['default']
=================================
1 default
```

+ **info [index or replica-id]** - show information about replica set  
Example: `info 1`  

```javascript
========= Response data =========
result code:  200
{'auth_key': None,
 'id': 'default',
 'members': [{'_id': 0, 'host': 'EPBYMINW0164T1:1025'},
              {'_id': 1, 'host': 'EPBYMINW0164T1:1026'},
              {'_id': 2, 'host': 'EPBYMINW0164T1:1027'},
              {'_id': 3, 'host': 'EPBYMINW0164T1:1028'}]}
=================================
```

+ **arbiters [index or replica-id]** - show list of arbiters hosts  
Example: `arbiters 1`  

```javascript
========= Response data =========
result code:  200
[{'_id': 2, 'host': 'EPBYMINW0164T1:1027'}]
=================================
```

+ **hidden [index or replica-id]** - show hidden hosts  
Example: `hidden 1`  

```javascript
========= Response data =========
result code:  200
[{'_id': 3, 'host': 'EPBYMINW0164T1:1028'}]
=================================
```

+ **secondaries** - show secondaries hosts  
Example: `secondaries [index or replica-id]`  

```javascript
========= Response data =========
result code:  200
[{'_id': 1, 'host': 'EPBYMINW0164T1:1026'},
 {'_id': 3, 'host': 'EPBYMINW0164T1:1028'}]
=================================
```

+ **primary [index or replica-id]** - show information about primary host  
Example: `primary 1`  

```javascript
========= Response data =========
result code:  200
{'_id': 0,
 'procInfo': {'alive': True,
               'name': 'mongod',
               'optfile': '/tmp/mongo-qiIHUz',
               'params': {'dbpath': '/tmp/mongo-tgT1tD',
                           'nojournal': 'true',
                           'noprealloc': 'true',
                           'oplogSize': 10,
                           'port': 1025,
                           'replSet': 'default',
                           'smallfiles': 'true'},
               'pid': 26806},
 'rsInfo': {'primary': True, 'secondary': False},
 'statuses': {'locked': False, 'mongos': False, 'primary': True},
 'uri': 'EPBYMINW0164T1:1025'}
=================================
```

+ **stepdown [index or replica-id]** - stepdown primary host  
Example: `stepdown 1`  

```javascript
========= Response data =========
result code:  200
''
=================================
```

+ **members** - show all replicaset's members  
Example: `members [index or replica-id]`  

```javascript
========= Response data =========
result code:  200
[{'_id': 0, 'host': 'EPBYMINW0164T1:1025'},
 {'_id': 1, 'host': 'EPBYMINW0164T1:1026'},
 {'_id': 2, 'host': 'EPBYMINW0164T1:1027'},
 {'_id': 3, 'host': 'EPBYMINW0164T1:1028'}]
=================================
```

+ **member_add [index or replica-id]  {member config}** - add new member to replica set  
Example: `member_add 1  {"rsParams": {"hidden": true, "priority": 0}}`  

```javascript
========= Response data =========
result code:  200
[{'_id': 0, 'host': 'EPBYMINW0164T1:1025'},
 {'_id': 1, 'host': 'EPBYMINW0164T1:1026'},
 {'_id': 2, 'host': 'EPBYMINW0164T1:1027'},
 {'_id': 3, 'host': 'EPBYMINW0164T1:1028'},
 {'_id': 4, 'host': 'EPBYMINW0164T1:1030'}]
=================================
```

+ **member_info [index or replica-id]  [member-id]** - show information about member  
Example: `member_info 1  4`  

```javascript
========= Response data =========
result code:  200
{'_id': 4,
 'procInfo': {'alive': True,
               'name': 'mongod',
               'optfile': '/tmp/mongo-XDk4wy',
               'params': {'dbpath': '/tmp/mongo-1KL3aQ',
                           'nojournal': 'true',
                           'noprealloc': 'true',
                           'oplogSize': 10,
                           'port': 1030,
                           'replSet': 'default',
                           'smallfiles': 'true'},
               'pid': 28377},
 'rsInfo': {'hidden': True, 'primary': False, 'secondary': True},
 'statuses': {'locked': False, 'mongos': False, 'primary': False},
 'uri': 'EPBYMINW0164T1:1030'}
=================================
```

+ **member_update [index or replica-id]  [member-id]** - update member params  
Example: `member_update 1  4  {"rsParams": {"hidden":false, "priority": 3}}`  

```javascript
========= Response data =========
result code:  200
{'_id': 4,
 'procInfo': {'alive': True,
               'name': 'mongod',
               'optfile': '/tmp/mongo-XDk4wy',
               'params': {'dbpath': '/tmp/mongo-1KL3aQ',
                           'nojournal': 'true',
                           'noprealloc': 'true',
                           'oplogSize': 10,
                           'port': 1030,
                           'replSet': 'default',
                           'smallfiles': 'true'},
               'pid': 28377},
 'rsInfo': {'primary': True, 'secondary': False},
 'statuses': {'locked': False, 'mongos': False, 'primary': True},
 'uri': 'EPBYMINW0164T1:1030'}
=================================
```

+ **member_command [index or replica-id]  [member-id]  [command]** - start/stop/restart host  
Example: `member_command 1  4  stop`  

```javascript
========= Response data =========
result code:  200
''
=================================
```

+ **member_freeze [index or replica-id]  [member-id]  [timeout]** - Forces the current node to become ineligible to become primary for the period specified  
Example: `member_freeze 1  1  60`  

```javascript
========= Response data =========
result code:  200
=================================
```

+ **member_delete [index or replcia-id]  [member-id]** - remove host from replica set  
Example: `member_delete 1  4`  

```javascript
========= Response data =========
result code:  200
True
=================================
```

+ **delete [index or replica-id]** - remove replica set  
Example: `delete 1`  

```javascript
========= Response data =========
result code:  204
''
=================================
```



### cmd_sh.py - manage shard cluster

command format: `command sh_id  [member_id]  [params]`  
**command** - command  
**sh_id** - shard cluster id or index
**member_id** - member id  
**params** - json string  

**Note: two space between args**

commands:
+ **help** - show help information
+ **create** - create new shard cluster

Example: 
```javascript
create create {"id": "shard_cluster_1", "routers": [{"port": 2323}, {}], "configsvrs": [{"port": 2315}], "members": [{"id": "sh01", "shardParams": {}}, {"id": "sh02", "shardParams": {"port": 2320}}, {"id": "sh-rs-01", "shardParams": {"id": "rs1", "members": [{}, {}]}}]}
```  

```javascript
========= Response data =========
result code:  200
{'configsvrs': [{'hostname': '127.0.0.1:2315',
                  'id': 'd28f2b3d-245f-4b3c-8dff-96a3d3a7ca7a'}],
 'id': 'shard_cluster_1',
 'members': [{'_id': '31ee0ea7-e7b7-4df4-b8fd-1e3cc5398b72',
               'id': 'sh01',
               'isHost': True},
              {'_id': 'rs1', 'id': 'sh-rs-01', 'isReplicaSet': True},
              {'_id': '67806256-fdd3-475d-a33f-b68302e74636',
               'id': 'sh02',
               'isHost': True}],
 'routers': [{'hostname': '127.0.0.1:2323',
               'id': '9f6b743b-24d2-40eb-860f-1b0c474625da'},
              {'hostname': '127.0.0.1:1025',
               'id': '84c7a69d-ea44-4b54-9525-c394b143c799'}]}
=================================
['shard_cluster_1']
```

+ **list** - show list of clusters , format: index cluster-id  
Example: `list`  

```javascript
========= Response data =========
result code:  200
['shard_cluster_1']
=================================
1 shard_cluster_1
```

+ **info [index or cluter-id]** - show info about cluster  
Example: `info 1`  

```javascript
========= Response data =========
result code:  200
{'configsvrs': [{'hostname': '127.0.0.1:2315',
                  'id': 'd28f2b3d-245f-4b3c-8dff-96a3d3a7ca7a'}],
 'id': 'shard_cluster_1',
 'members': [{'_id': '31ee0ea7-e7b7-4df4-b8fd-1e3cc5398b72',
               'id': 'sh01',
               'isHost': True},
              {'_id': 'rs1', 'id': 'sh-rs-01', 'isReplicaSet': True},
              {'_id': '67806256-fdd3-475d-a33f-b68302e74636',
               'id': 'sh02',
               'isHost': True}],
 'routers': [{'hostname': '127.0.0.1:2323',
               'id': '9f6b743b-24d2-40eb-860f-1b0c474625da'},
              {'hostname': '127.0.0.1:1025',
               'id': '84c7a69d-ea44-4b54-9525-c394b143c799'}]}
=================================
```

+ **configservers [index or cluster-id]** - show list of config servers  
Example: `configservers 1`  

```javascript
========= Response data =========
result code:  200
[{'hostname': '127.0.0.1:2315',
  'id': 'd28f2b3d-245f-4b3c-8dff-96a3d3a7ca7a'}]
=================================
```

+ **routers [index or cluster-id]** - show routers  
Example: `routers 1`  

```javascript
========= Response data =========
result code:  200
[{'hostname': '127.0.0.1:2315',
  'id': 'd28f2b3d-245f-4b3c-8dff-96a3d3a7ca7a'}]
=================================
```

+ **router_add** - add new router  
Example: `router_add [index or cluster-id]  {"port": 2525, "logpath": "/tmp/router2"}`  

```javascript
========= Response data =========
result code:  200
{'hostname': '127.0.0.1:2525',
 'id': 'eae3af8c-c8b0-4e69-85f9-fab69ef51b32'}
=================================
```

+ **router_delete** - delete router
Example: `router_add [index or cluster-id] [router-id]`

```javascript
========= Response data =========
result code:  200
{'ok': 1,
 'routers': [u'e5858165-929b-48bc-ac0d-87cf31655ea8', u'302ed013-5ce7-45e0-b5ba-132e6d52caec']}
=================================
```

+ **members** - show cluster's members  
Example: `members [index or cluster-id]`  

```javascript
========= Response data =========
result code:  200
[{'_id': '31ee0ea7-e7b7-4df4-b8fd-1e3cc5398b72',
  'id': 'sh01',
  'isHost': True},
 {'_id': 'rs1', 'id': 'sh-rs-01', 'isReplicaSet': True},
 {'_id': '67806256-fdd3-475d-a33f-b68302e74636',
  'id': 'sh02',
  'isHost': True}]
=================================
```

+ **member_add [index or cluster-id]  {member config}** - add new member to cluster  
Example: `member_add 1  {"id": "shardX", "shardParams": {"port": 2527, "dbpath": "/tmp/memberX", "logpath": "/tmp/memberX.log", "ipv6": true, "nojournal": true}}`   

```javascript
========= Response data =========
result code:  200
{'_id': 'b380299e-6edf-4445-9f86-327a44fb9c1d',
 'id': 'shardX',
 'isHost': True}
=================================
```

+ **member_add [index or cluster-id]  {member config}** - add new member to cluster  
Example: `member_add 1  {"id": "shard-rs", "shardParams": {"id": "repl-test", "members": [{}, {}, {"rsParams": {"arbiterOnly": true}}]}}`   

```javascript
========= Response data =========
result code:  200
{'_id': 'repl-test', 'id': 'shard-rs', 'isReplicaSet': True}
=================================
```

+ **member_info [index or cluster-id]  [member-id]** - show information about member  
Example: `member_info 1  shardX`  

```javascript
========= Response data =========
result code:  200
{'_id': 'b380299e-6edf-4445-9f86-327a44fb9c1d',
 'id': 'shardX',
 'isHost': True}
=================================
```

+ **member_info [index or cluster-id]  [member-id]** - show information about member  
Example: `member_info 1  shard-rs`  

```javascript
========= Response data =========
result code:  200
{'_id': 'repl-test', 'id': 'shard-rs', 'isReplicaSet': True}
=================================
```

+ **member_delete [index or cluster-id]  [member-id]** - remove sahrd from cluster  
Example: `member_delete 1  sh01`  

```javascript
========= Response data =========
result code:  200
{'msg': 'draining started successfully',
 'ok': 1.0,
 'shard': 'sh01',
 'state': 'started'}
=================================
```

+ **member_delete [index or cluster-id]  [member-id]** - remove shard from cluster  
Example: `member_delete 1  sh01`  

```javascript
========= Response data =========
result code:  200
{'msg': 'removeshard completed successfully',
 'ok': 1.0,
 'shard': 'sh01',
 'state': 'completed'}
=================================
```

+ **delete [index or cluster-id]** - remove cluster  
Example: `delete shard_cluster_1`  

```javascript
========= Response data =========
result code:  204
''
=================================
```

##Tests

###Run all tests

`nosetests tests`

###Run a test file example

`nosetests tests/test_hosts.py`

###Run a single test example

`nosetests tests/test_hosts.py:HostTestCase.test_info`

###Run a single test example for debugging with verbose and immediate stdout output

`nosetests -vs tests/test_hosts.py:HostTestCase.test_info`
