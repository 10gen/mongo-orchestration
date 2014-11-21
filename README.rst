See the `wiki <https://github.com/mongodb/mongo-orchestration/wiki>`__
for documentation.

Mongo Orchestration is an HTTP server that provides a REST API for
creating and managing MongoDB configurations.

Features
--------

-  Start and stop mongod servers, replica sets, and sharded clusters.
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
-  `PyMongo >= 2.7.2 <https://pypi.python.org/pypi/pymongo>`__
-  `CherryPy >= 3.5.0 <http://www.cherrypy.org/>`__
-  `argparse >= 1.2.1 <https://pypi.python.org/pypi/argparse>`__ (Python 2.6 only)

Installation
------------

The easiest way to install Mongo Orchestration is with `pip <https://pypi.python.org/pypi/pip>`__:

::

    pip install mongo-orchestration

You can also install the development version of Mongo Orchestration
manually:

::

    git clone https://github.com/mongodb/mongo-orchestration.git
    cd mongo-orchestration
    python setup.py install

Cloning the repository this way will also give you access to `predefined configurations`_ for Mongo Orchestration as well as the "mo" script. Note that you may
have to run the above commands with ``sudo``, depending on where you're
installing Mongo Orchestration and what privileges you have.
Installation will place a ``mongo-orchestration`` script on your path.

Usage
-----

``mongo-orchestration [-h] [-f CONFIG] [-e ENV] [--no-fork] [-p PORT] {start,stop,restart}``

Arguments:

-  **-h** - show help
-  **-f, --config** - path to config file
-  **-e, --env** - default release to use, as specified in the config
   file
-  **--no-fork** - run server in foreground
-  **-p** - port number (8889 by default)
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

``mongo-orchestration -f mongo-orchestration.config -e 26-release -p 8888 --no-fork start``

Starts Mongo Orchestration on port 8888 using ``26-release`` defined in
``mongo-orchestration.config``. Stops with *Ctrl+C*.

Configuration File
~~~~~~~~~~~~~~~~~~

Mongo Orchestration may be given a JSON configuration file with the
``--config`` option specifying where to find MongoDB binaries. See
`mongo-orchestration.config <https://github.com/mongodb/mongo-orchestration/blob/master/mongo-orchestration.config>`__
for an example. When no configuration file is provided, Mongo
Orchestration uses whatever binaries are on the user's PATH.

Predefined Configurations
-------------------------

The Mongo Orchestration repository has a set of predefined
`configurations <https://github.com/mongodb/mongo-orchestration/tree/master/mongo_orchestration/configurations>`__
that can be used to start, restart, or stop MongoDB processes. You can
use a tool like ``curl`` to send these files directly to the Mongo
Orchestration server, or use the ``mo`` script in the ``scripts``
directory. Some examples:

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
                "noprealloc": true,
                "oplogSize": 100,
                "port": 1025,
                "smallfiles": true
            },
            "pid": 51320
        },
        // etc.
    }

Tests
-----

Running the tests has the following additional dependencies:

-  `nose >= 1.3.4 <https://pypi.python.org/pypi/nose>`__
-  `unittest2 >= 0.6 <https://pypi.python.org/pypi/unittest2>`__ (Python 2.6 only)

Run all tests
~~~~~~~~~~~~~

``nosetests tests``

Run a test file example
~~~~~~~~~~~~~~~~~~~~~~~

``nosetests tests/test_hosts.py``

Run a single test example
~~~~~~~~~~~~~~~~~~~~~~~~~

``nosetests tests/test_hosts.py:HostTestCase.test_info``

Run a single test example for debugging with verbose and immediate stdout output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``nosetests -vs tests/test_hosts.py:HostTestCase.test_info``
