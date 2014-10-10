[![Build Status](https://jenkins.10gen.com/job/mongo-orchestration/badge/icon)](https://jenkins.10gen.com/job/mongo-orchestration/)


See the [wiki](https://github.com/mongodb/mongo-orchestration/wiki) for documentation.

Mongo Orchestration is an HTTP server that provides a REST API for creating and managing MongoDB configurations.

##Features

- Start and stop mongod servers, replica sets, and sharded clusters.
- Add and remove replica set members.
- Add and remove shards and mongos routers.
- Reset replica sets and clusters to restart all members that were stopped.
- Freeze secondary members of replica sets.
- Retrieve information about MongoDB resources.
- Interaction all through REST interface.

##Requires
- [Python 2.6, 2.7, or >= 3.2](http://www.python.org/download/)
- [PyMongo 2.7.2](https://pypi.python.org/pypi/pymongo/2.7.2)
- [CherryPy 3.5.0](http://www.cherrypy.org/)

##Installation

Install Mongo Orchestration using `python setup.py install`. Note that this may require administrator privileges. This will place a script called `mongo-orchestration` on your path, can be used to control the Mongo Orchestration server.

##Usage
`mongo-orchestration [-h] [-f CONFIG] [-e ENV] [--no-fork] [-p PORT] {start,stop,restart}`

Arguments:

+ **-h** - show help
+ **-f, --config** - path to config file
+ **-e, --env** - default release to use, as specified in the config file
+ **--no-fork** - run server in foreground
+ **-p** - port number (8889 by default)
+ **start/stop/restart**: start, stop, or restart the server, respectively

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

## Predefined Configurations
The Mongo Orchestration repository has a set of predefined [configurations](https://github.com/mongodb/mongo-orchestration/tree/master/configurations) that can be used to start, restart, or stop MongoDB processes. You can use a tool like `curl` to send these files directly to the Mongo Orchestration server, or use the `mo` script in the `scripts` directory. Some examples:

- Start a single node without SSL or auth:

        scripts/mo configurations/servers/clean.json start

- Get the status of a single node without SSL or auth:

        scripts/mo configurations/servers/clean.json status

- Stop a single node without SSL or auth:

        scripts/mo configurations/servers/clean.json stop

- Start a replica set with ssl and auth:

        scripts/mo configurations/replica_sets/ssl_auth.json start

##Tests

###Run all tests

`nosetests tests`

###Run a test file example

`nosetests tests/test_hosts.py`

###Run a single test example

`nosetests tests/test_hosts.py:HostTestCase.test_info`

###Run a single test example for debugging with verbose and immediate stdout output

`nosetests -vs tests/test_hosts.py:HostTestCase.test_info`
