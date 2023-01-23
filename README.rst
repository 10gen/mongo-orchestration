-------------------
Mongo Orchestration
-------------------

See the `wiki <https://github.com/10gen/mongo-orchestration/wiki>`__
for documentation.

Mongo Orchestration is an HTTP server that provides a REST API for
creating and managing MongoDB configurations on a single host.

**THIS PROJECT IS FOR TESTING OF MONGODB DRIVERS.**

Features
--------

-  Start and stop mongod servers, replica sets, and sharded clusters on the host running mongo-orchestration.
-  Add and remove replica set members.
-  Add and remove shards and mongos routers.
-  Reset replica sets and clusters to restart all members that were
   stopped.
-  Freeze secondary members of replica sets.
-  Retrieve information about MongoDB resources.
-  Interaction all through REST interface.

Requires
--------

-  `Python 2.6, 2.7, or >= 3.2 <http://www.python.org/download/>`__
-  `bottle>=0.12.7 <https://pypi.python.org/pypi/bottle>`__
-  `pymongo>=3.0.2,<4 <https://pypi.python.org/pypi/pymongo>`__
-  `cheroot>=5.11 <https://pypi.python.org/pypi/cheroot/>`__
-  `argparse>=1.2.1 <https://pypi.python.org/pypi/argparse>`__ (Python 2.6 only)
-  `simplejson <https://pypi.python.org/pypi/simplejson>`__ (Python 2.6 only)

Installation
------------

The easiest way to install Mongo Orchestration is with `pip <https://pypi.python.org/pypi/pip>`__:

::

    pip install mongo-orchestration

You can also install the development version of Mongo Orchestration
manually:

::

    git clone https://github.com/10gen/mongo-orchestration.git
    cd mongo-orchestration
    pip install .

Cloning the `repository <https://github.com/10gen/mongo-orchestration>`__ this way will also give you access to the tests for Mongo Orchestration as well as the ``mo`` script. Note that you may
have to run the above commands with ``sudo``, depending on where you're
installing Mongo Orchestration and what privileges you have.
Installation will place a ``mongo-orchestration`` script on your path.

Usage
-----

::

    mongo-orchestration [-h] [-f CONFIG] [-e ENV] [--no-fork] [-b BIND IP="localhost"] [-p PORT]
                        [-s {auto,cheroot,wsgiref}] [--socket-timeout-ms MILLIS]
                        [--pidfile PIDFILE] [--enable-majority-read-concern] {start,stop,restart}


Arguments:

-  **-h** - show help
-  **-f, --config** - path to config file
-  **-e, --env** - default release to use, as specified in the config
   file
-  **--no-fork** - run server in foreground
-  **-b, --bind** - host on which Mongo Orchestration and subordinate mongo processes should listen for requests. Defaults to "localhost".
-  **-s, --server** - HTTP backend to use: one of `auto`, `cheroot`, or `wsgiref`. `auto`
   configures bottle to automatically choose an available backend.
-  **-p** - port number (8889 by default)
-  **--socket-timeout-ms** - socket timeout when connecting to MongoDB servers
-  **--pidfile** - location where mongo-orchestration should place its pid file
-  **--enable-majority-read-concern** - enable "majority" read concern on server versions that support it.
-  **start/stop/restart**: start, stop, or restart the server,
   respectively

In addition, Mongo Orchestration can be influenced by the
``MONGO_ORCHESTRATION_HOME`` environment variable, which informs the
server where to find the "configurations" directory for presets as well
as where to put the log and pid files.

Examples
~~~~~~~~

``mongo-orchestration start``

Starts Mongo Orchestration as service on port 8889.

``mongo-orchestration stop``

Stop the server.

``mongo-orchestration -f mongo-orchestration.config -e 30-release -p 8888 --no-fork start``

Starts Mongo Orchestration on port 8888 using ``30-release`` defined in
``mongo-orchestration.config``. Stops with *Ctrl+C*.

If you have installed mongo-orchestration but you're still getting
``command not found: mongo-orchestration`` this means that the script was
installed to a directory that is not on your ``PATH``. As an alternative use:

``python -m mongo_orchestration.server start``

Configuration File
~~~~~~~~~~~~~~~~~~

Mongo Orchestration may be given a JSON configuration file with the
``--config`` option specifying where to find MongoDB binaries. See
`mongo-orchestration.config <https://github.com/10gen/mongo-orchestration/blob/master/mongo-orchestration.config>`__
for an example. When no configuration file is provided, Mongo
Orchestration uses whatever binaries are on the user's PATH.

Predefined Configurations
-------------------------

Mongo Orchestration has a set of predefined
`configurations <https://github.com/10gen/mongo-orchestration/tree/master/mongo_orchestration/configurations>`__
that can be used to start, restart, or stop MongoDB processes. You can
use a tool like ``curl`` to send these files directly to the Mongo
Orchestration server, or use the ``mo`` script in the ``scripts``
directory (in the `repository <https://github.com/10gen/mongo-orchestration>`__ only). Some examples:

-  Start a single node without SSL or auth:

   ::

       mo configurations/servers/clean.json start

-  Get the status of a single node without SSL or auth:

   ::

       mo configurations/servers/clean.json status

-  Stop a single node without SSL or auth:

   ::

       mo configurations/servers/clean.json stop

-  Start a replica set with ssl and auth:

   ::

       mo configurations/replica_sets/ssl_auth.json start

-  Use ``curl`` to create a basic sharded cluster with the id
   "myCluster":

   ::

       curl -XPUT http://localhost:8889/v1/sharded_clusters/myCluster \
                  -d@configurations/sharded_clusters/basic.json

Note that in order to run the ``mo`` script, you need to be in the same
directory as "configurations".

**Helpful hint**: You can prettify JSON responses from the server by
piping the response into ``python -m json.tool``, e.g.:

::

    $ curl http://localhost:8889/v1/servers/myServer | python -m json.tool

    {
        "id": "myServer",
        "mongodb_uri": "mongodb://localhost:1025",
        "orchestration": "servers",
        "procInfo": {
            "alive": true,
            "name": "mongod",
            "optfile": "/var/folders/v9/spc2j6cx3db71l/T/mongo-KHUACD",
            "params": {
                "dbpath": "/var/folders/v9/spc2j6cx3db71l/T/mongo-vAgYaQ",
                "ipv6": true,
                "journal": true,
                "logappend": true,
                "oplogSize": 100,
                "port": 1025
            },
            "pid": 51320
        },
        // etc.
    }

Tests
-----

In order to run the tests, you should first clone the `repository <https://github.com/10gen/mongo-orchestration>`__. Running the tests has the following additional dependency:

-  `unittest2 >= 0.6 <https://pypi.python.org/pypi/unittest2>`__ (Python 2.6 only)

Run all tests
~~~~~~~~~~~~~

``python setup.py test``

Run a test module
~~~~~~~~~~~~~~~~~

``python -m unittest tests.test_servers``

Run a single test case
~~~~~~~~~~~~~~~~~~~~~~

``python -m unittest tests.test_servers.ServerSSLTestCase``

Run a single test method
~~~~~~~~~~~~~~~~~~~~~~~~

``python -m unittest tests.test_servers.ServerSSLTestCase.test_ssl_auth``

Run a single test example for debugging with verbose and immediate stdout output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``python -m unittest -v tests.test_servers.ServerSSLTestCase``

Changelog
---------

Changes in Version 0.7.1 (TBD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Replaced dependency on CherryPy with cheroot. `-s auto` is the new default
  and `-s cherrypy` is no longer supported.
- Remove transactionLifetimeLimitSeconds default.

Changes in Version 0.7.0 (2021-04-06)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Remove support for managing MongoDB 2.4 servers.
- Add support for Python 3.8 and 3.9.
- Add support for MongoDB 4.2 and 4.4.
- Upgrade from pymongo 3.5.1 to 3.X latest. (#284).
- Ensure createUser succeeds on all replica set members. (#282)
- Create admin user with both SCRAM-SHA-256 and SCRAM-SHA-1. (#281)
- Wait for mongo-orchestration server to fully terminate in "stop". (#276)
- Allow starting clusters with enableTestCommands=0. (#269)
- Decrease transactionLifetimeLimitSeconds on 4.2+ by default. (#267)
- Increase maxTransactionLockRequestTimeoutMillis by default. (#270)
- Reduce periodicNoopIntervalSecs for faster driver change stream testing. (#283)
- Enable ztsd compression by default on 4.2+ (#263)

Changes in Version 0.6.12 (2018-12-14)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Allow running the mongo-orchestration server over IPv6 localhost. (#237)
- Increase default mongodb server logging verbosity. (#255)
- Fixed a bug when shutting down clusters where mongo-orchestration would
  hang forever if the server had already exited. (#253)
