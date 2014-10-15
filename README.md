**mongo-orchestration** - http server which provide rest api to management mongo's configurations

See the [wiki](https://github.com/mongodb/mongo-orchestration/wiki) for documentation.

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
- [Python 2.6, 2.7, or >= 3.2](http://www.python.org/download/)
- [requests](http://docs.python-requests.org/en/latest/user/install/#install)
- [PyMongo 2.7.2](https://pypi.python.org/pypi/pymongo/2.7.2)
- [CherryPy 3.5.0](http://www.cherrypy.org/)

##Installing

Install Mongo Orchestration using `python setup.py install`. Note that this may require administrator privileges. This will place a script called `mongo-orchestration` on your path, which you can use to control the Mongo Orchestration server.

##Usage
`mongo-orchestration [-h] [-f CONFIG] [-e ENV] [--no-fork] [-p PORT] {start,stop,restart}`

Arguments:
+ **-h** - show help info
+ **-f, --config** - path to config file
+ **-e, --env** - release name from config file
+ **--no-fork** - don't start as service
+ **-p** - port number, 8889 by default
+ **start/stop/restart**: server's command

In addition, Mongo Orchestration can be influenced by the `MONGO_ORCHESTRATION_HOME` environment variable, which informs the server where to find the "configurations" directory for presets.

###Examples

`mongo-orchestration start`

Starts Mongo Orchestration as service on port 8889.

`mongo-orchestration stop`

Stop the server.

`mongo-orchestration -f mongo-orchestration.config -e 26-release -p 8888 --no-fork start`

Starts Mongo Orchestration on port 8888 using `26-release` defined in `mongo-orchestration.config`. Stops with *Ctrl+C*.

###Configuration File
Mongo Orchestration may be given a JSON configuration file with the `--config` option specifying where to find MongoDB binaries. See [`mongo-orchestration.config`](https://github.com/mongodb/mongo-orchestration/blob/master/mongo-orchestration.config) for an example. When no configuration file is provided, Mongo Orchestration uses whatever binaries are on the user's PATH.

## Predefined configurations
There is a set of predefined configurations in the repository. They can be started with the `mo` script from the `scripts` folder.

To start a single node without ssl or auth:
```bash
scripts/mo configurations/hosts/clean.json start
```

To get status on a single node without ssl or auth:
```bash
scripts/mo configurations/hosts/clean.json status

To stop a single node without ssl or auth:
```bash
scripts/mo configurations/hosts/clean.json stop

To start a single node with ssl, but no auth:
```bash
scripts/mo configurations/hosts/ssl.json start
```

To start a replica set with ssl and auth:
```bash
scripts/mo configurations/rs/ssl_auth.json start
```

To start a sharded cluster with auth:
```bash
scripts/mo configurations/sh/auth.json start
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
