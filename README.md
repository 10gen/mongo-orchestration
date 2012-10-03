# REST API to manage mongos instances #

## Defined terms ##

### Type of Collections ###
+ **hs** - Hosts
+ **ms** - Master-Slave (each *ms* contains one *hs* collection)
+ **rs** - ReplicaSet (each *rs* contains one *hs* collection)
+ **sd** - Shard (each *sd* contains at least one *rs* collection)

ReplicaSet *rs*, Shard *sd* and Master-Slave *ms* collections should contains Hosts *hs* collection.  
Shard *sd* collection should contain at least one *rs* collection.  

### Host object ###
Most of requests return a host object as result.
Host object is a *mongod* or *mongos* process.

#### Host Object Command ####
+ **start**   -   get up host
+ **stop**    -   stop host (data doesn't remove)
+ **restart** -   restart host

##### Stop vs DELETE #####
Command `stop` stoped host, but doesn't remove any items from file system.  
Method `DELETE` stoped host and remove hosts items from file system (log file, db folder, ...)


## REST API INDEX ##
### Hosts ###
+ [/hs](#hosts-1) [POST]  

#### Host Object ####
+ [/hs/{id}](#host-object-2) [GET, DELETE]  
  - [/hs/{id}/start](#host-object-2) [PUT]  
  - [/hs/{id}/stop](#host-object-2) [PUT]  
  - [/hs/{id}/restart](#host-object-2) [PUT]  

### Master-Slave ###
+ [/ms](#master-slave-1) [POST]  
  - [/ms/{id}](#master-slave-1) [GET, DELETE]  
  - [/ms/{id}/hs](#master-slave-1) [POST]  

### ReplicaSet ###
+ [/rs](#replicaset-1) [POST]  
    - [/rs/{id}](#replicaset-1) [GET, DELETE]  
    - [/rs/{id}/hosts](#replicaset-1) [GET]  
    - [/rs/{id}/hs](#rs-hosts) [POST]  
         * [/rs/{id}/hs/{id}](#host-object-2) [GET, DELETE]  
         * [/rs/{id}/hs/{id}/start](#host-object-2) [PUT]  
         * [/rs/{id}/hs/{id}/stop](#host-object-2) [PUT]  
         * [/rs/{id}/hs/{id}/restart](#host-object-2) [PUT]  
  - [/rs/{id}/primary](#rs-primary) [GET, DELETE]  
       * [/rs/{id}/primary/stepdown](#rs-primary) [PUT]  
       * [/rs/{id}/primary/start](#host-object-2) [PUT]  
       * [/rs/{id}/primary/stop](#host-object-2) [PUT]  
       * [/rs/{id}/primary/restart](#host-object-2) [PUT]  
  - [/rs/{id}/secondaries](#rs-secondaries) [GET, DELETE]  
        * [/rs/{id}/secondaries/random](#rs-secondaries) [GET]  
            * [/rs/{id}/secondaries/random/start](#host-object-2) [PUT]  
            * [/rs/{id}/secondaries/random/stop](#host-object-2) [PUT]  
            * [/rs/{id}/secondaries/random/restart](#host-object-2) [PUT]  
        * [/rs/{id}/secondaries/{id}](#host-object-2) [GET]  
            * [/rs/{id}/secondaries/{id}/start](#host-object-2) [PUT]  
            * [/rs/{id}/secondaries/{id}/stop](#host-object-2) [PUT]  
            * [/rs/{id}/secondaries/{id}/restart](#host-object-2) [PUT]  
  - [/rs/{id}/arbiters](#rs-arbiters) [GET, DELETE]  
        * [/rs/{id}/arbiters/random](#rs-arbiters) [GET]  
            * [/rs/{id}/arbiters/random/start](#host-object-2) [PUT]  
            * [/rs/{id}/arbiters/random/stop](#host-object-2) [PUT]  
            * [/rs/{id}/arbiters/random/restart](#host-object-2) [PUT]  
        * [/rs/{id}/arbiters/{id}](#host-object-2) [GET]  
            * [/rs/{id}/arbiters/{id}/start](#host-object-2) [PUT]  
            * [/rs/{id}/arbiters/{id}/stop](#host-object-2) [PUT]  
            * [/rs/{id}/arbiters/{id}/restart](#host-object-2) [PUT]  
  - [/rs/{id}/hidden](#rs-hidden) [GET, DELETE]  
        * [/rs/{id}/hidden/random](#rs-hidden) [GET]  
        * [/rs/{id}/hidden/random/start](#host-object-2) [PUT]  
        * [/rs/{id}/hidden/random/stop](#host-object-2) [PUT]  
        * [/rs/{id}/hidden/random/restart](#host-object-2) [PUT]  

### Shards ###
+ [/sd](#shards-1) [POST]  
    - [/sd/{id}](#shards-1) [GET, DELETE]  
    - [/sd/{id}/rs](#shard-replicaset) [GET]  
  - [/sd/{id}/configsvrs](#shard-config-servers) [GET, DELETE]  
        * [/sd/{id}/configsvrs/random](#shard-config-servers) [GET]  
            * [/sd/{id}/configsvrs/random/start](#host-object-2) [PUT]  
            * [/sd/{id}/configsvrs/random/stop](#host-object-2) [PUT]  
            * [/sd/{id}/configsvrs/random/restart](#host-object-2) [PUT]  
        * [/sd/{id}/configsvrs/{id}](#host-object-2) [GET]  
            * [/rs/{id}/configsvrs/{id}/start](#host-object-2) [PUT]  
            * [/rs/{id}/configsvrs/{id}/stop](#host-object-2) [PUT]  
            * [/rs/{id}/configsvrs/{id}/restart](#host-object-2) [PUT]  
  - [/sd/{id}/mongos](#shard-mongos-instances) [GET, DELETE]  
        * [/sd/{id}/mongos/random](#shard-mongos-instances) [GET]  
            * [/sd/{id}/mongos/random/start](#host-object-2) [PUT]  
            * [/sd/{id}/mongos/random/stop](#host-object-2) [PUT]  
            * [/sd/{id}/mongos/random/restart](#host-object-2) [PUT]  
        * [/sd/{id}/mongos/{id}](#host-object-2) [GET]  
            * [/rs/{id}/mongos/{id}/start](#host-object-2) [PUT]  
            * [/rs/{id}/mongos/{id}/stop](#host-object-2) [PUT]  
            * [/rs/{id}/mongos/{id}/restart](#host-object-2) [PUT]  
  - [/sd/{id}/hosts](#shard-hosts) [GET, DELETE]  
        * [/sd/{id}/hosts/random](#shard-hosts) [GET]  
        * [/sd/{id}/hosts/random/start](#host-object-2) [PUT]  
        * [/sd/{id}/hosts/random/stop](#host-object-2) [PUT]  
        * [/sd/{id}/hosts/random/restart](#host-object-2) [PUT]  
  - [/sd/{id}/hs](#shard-hosts) [POST]  
       * [/sd/{id}/hs/{id}](#host-object-2) [GET, DELETE]  
       * [/sd/{id}/hs/{id}/start](#host-object-2) [PUT]  
       * [/sd/{id}/hs/{id}/stop](#host-object-2) [PUT]  
       * [/sd/{id}/hs/{id}/restart](#host-object-2) [PUT]  

## REST API RESOURCES ##
### Hosts ###
URI: `/hs`  
Create new mongo instance  
*Methods*:  
**POST**    - create and get up new host   
*available response representations:*  
  + 200 - Returned if create host was successful
  + 500 - Returned if create host was fail  

Example:  

    {
     
    }
  

##### Host Object #####
URI: `/hs/{id}`  
*Methods*:  
**GET**     - returns info about host  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the host does not exist  

Example:  

    {
    "id": "ad19921c-6ab9-44f7-9be9-19fd5e89561d",
    "uri": "192.168.1.0:2233",
    "statuses": {"primary": true, "mongos": false, "locked": false},
    "serverInfo": {"sysInfo": "Linux ip-10-2-29-40 2.6.21.7-2.ec2.v1.2.fc8xen #1 SMP Fri Nov 20 17:48:28 EST 2009 x86_64 BOOST_LIB_VERSION=1_49", 
                  "version": "2.2.0", "debug": False, "maxBsonObjectSize": 16777216, "bits": 64, 
                  "gitVersion": "f5e83eae9cfbec7fb7a071321928f00d1b0c5207"},
    "procInfo": {"name": "mongod", "alive": true, params: {}}
    }

**DELETE**  - remove host with all data (log file, db files, ...)  
*available response representations:*  
  + 204 - Returned if delete was successful 
  + 400 - Returned if delete was fail 


URI: `/hs/{id}/start`  
Get up existing host.  
*Parameters*:  
**timeout** - specify how long, in seconds, a command can take before server times out.  
*Methods*:  
**PUT** - get up host  
*acceptable request representations:*  application/json  

Example:

    {
      "timeout": 300
    }
*available response representations:*  
  + 200 - if the host started successfully  
  + 500 - if an error occurred when starting host  


URI: `/hs/{id}/stop`  
Stop existing host  
*Parameters*:  
**timeout** - specify how long, in seconds, a command can take before server times out.  
*Methods*:  
**PUT**  - stop host (data files don't remove)  
*acceptable request representations:*  application/json  
Example:

    {
      "timeout": 300
    }
*available response representations:*  
  + 200 - if the host stoped successfully  
  + 500 - if an error occurred when stoping host  


URI: `/hs/{id}/restart`  
Restart existing host  
*Parameters*:  
**timeout** - specify how long, in seconds, a command can take before server times out.  
*Methods*:  
**PUT** - restart host  
*acceptable request representations:*  application/json  
Example:

    {
      "timeout": 300
    }
*available response representations:*  
  + 200 - if the host restarted successfully  
  + 500 - if an error occurred when restarting host  



### Master-Slave ###
URI: `/ms`  
*Methods*:  
**POST** - create new Master-Slave configuration  
*available response representations:*  
  + 200 - Returned if create Master-Slave was successful
  + 500 - Returned if create Master-Slave was fail  

Example:

    {

    }

URI: `/ms/{id}`  
*Methods*:  
**GET**     - returns info about Master-Slave configuration  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the Master-Slave not exist  

Example:  

    {
    
    }

**DELETE** - remove Master-Slave configuration  
*available response representations:*  
  + 204 - Returned if delete was successful 
  + 400 - Returned if delete was fail 



##### MS Hosts #####
URI: `/ms/{id}/hs`  
see [Host](#hosts-1) Collection

URI: `/ms/{id}/hs/{id}`  
see [Host Object](#host-object-2)  

### ReplicaSet ###
URI: `/rs`  
*Methods*:  
**POST** - create and get up new ReplicaSet  
*available response representations:*  
  + 200 - Returned if create replica set was successful  
  + 500 - Returned if create replica set was fail  

Example:

    {

    }

URI: `/rs/{id}`  
*Methods*:  
**GET** - return info about ReplicaSet object  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the ReplicaSet not exist  

Example:  

    {
    
    }

**DELETE** - remove ReplicaSet  
*available response representations:*  
  + 204 - Returned if delete was successful 
  + 400 - Returned if delete was fail 


##### RS Hosts #####
URI: `/rs/{id}/hosts`  
*Methods*:  
**GET** - return list of ReplicaSets hosts  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the ReplicaSet not exist  

Example:  

    {
      
    }


URI: `/rs/{id}/hs`  
see [Host](#hosts-1) Collection

URI: `/rs/{id}/hs/{id}`  
see [Host Object](#host-object-2)  

##### RS Primary #####
URI: `/rs/{id}/primary`  
*Methods*:  
**GET** - return primary host of ReplicaSet  
**DELETE** - remove primary host of ReplicaSet   
see [Host Object](#host-object-2)  

URI: `/rs/{id}/primary/stepdown`  
*Methods*:  
**PUT** - forces the primary of the replica set to relinquish its status as primary  
*acceptable request representations:*  application/json  

Example:

    {
      "timeout": 300
    }
*available response representations:*  
  + 200 - if the primary stepdown successfully  
  + 500 - if an error occurred when stepdown primary host  


`/rs/{id}/primary/start`  
`/rs/{id}/primary/stop`  
`/rs/{id}/primary/restart`  
see [Host Object](#host-object-2)  

##### RS Secondaries #####
URI: `/rs/{id}/secondaries`  
*Methods*:  
**GET** - returl list of secondaries hosts  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the ReplicaSet not exist  

Example:  

    {
      
    }

**DELETE** - remove all secondaries hosts   
*available response representations:*  
  + 204 - Returned if delete was successful  
  + 400 - Returned if delete was fail  


URI: `/rs/{id}/secondaries/random`  
*Methods*:  
**GET** - return random [Host Object](#host-object-2) from secondaries  

URI: `/rs/{id}/secondaries/{id}`  
*Methods*:  
**GET** -return [Host Object](#host-object-2) from secondaries  

##### RS Arbiters #####
URI: `/rs/{id}/arbiters`  
*Methods*:  
**GET** - return list of all arbiters for ReplicaSet  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the ReplicaSet not exist  

Example:  

    {
      
    }

**DELETE** - remove all ReplicaSets arbiters   
*available response representations:*  
  + 204 - Returned if delete was successful  
  + 400 - Returned if delete was fail 


URI: `/rs/{id}/arbiters/random`  
*Methods*:  
**GET** -return random [Host Object](#host-object-2) from arbiters  

URI: `/rs/{id}/arbiters/{id}`  
*Methods*:  
**GET** -return [Host Object](#host-object-2) from arbiters  

##### RS Hidden #####
URI: `/rs/{id}/hidden`  
*Methods*:  
**GET** - returl list of all hidden hosts from ReplicaSet  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the ReplicaSet not exist  

Example:  

    {
      
    }

**DELETE** - remove all hidden hosts from ReplicaSet   
*available response representations:*  
  + 204 - Returned if delete was successful 
  + 400 - Returned if delete was fail 


URI: `/rs/{id}/hidden/random`  
*Methods*:  
**GET** - return random [Host Object](#host-object-2) from hidden  


### Shards ###
URI: `/sd`  
*Methods*:  
**POST** - create and get up new Shard Cluster  
*available response representations:*  
  + 200 - Returned if create shard cluster was successful  
  + 500 - Returned if create shard cluster set was fail  

Example:

    {

    }

URI: `/sd/{id}`  
*Methods*:  
**GET** - return info about Shard object  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the Shard not exist  

Example:  

    {
    
    }

**DELETE** - remove Shard Cluster  
*available response representations:*  
  + 204 - Returned if delete was successful  
  + 400 - Returned if delete was fail 


##### Shard ReplicaSet #####
URI: `/sd/{id}/rs`  
see [ReplicaSet](#replicaset-1) Collection

URI: `/sd/{id}/rs/{id}`  
see [ReplicaSet Object](#replicaset-1)  


##### Shard Config Servers #####
URI: `/sd/{id}/configsvrs`  
*Methods*:  
**GET** - return list of Config Servers  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the Shard Cluster not exist  

Example:  

    {
      
    }


URI: `/sd/{id}/configsvrs/{id}`  
see [Host Object](#host-object-2)  

URI: `/sd/{id}/configsvrs/random`  
see [Host Object](#host-object-2)  


##### Shard Mongos Instances #####
URI: `/sd/{id}/mongos`  
*Methods*:  
**GET** - return list of all mongos instances  
**DELETE** - remove all mongos instances   
see [Host Object](#host-object-2)  

URI: `/sd/{id}/mongos/{id}`  
*Methods*:  
**GET** - return info about mongos host  
**DELETE** - remove mongos instance   
see [Host Object](#host-object-2)  


`/sd/{id}/mongos/{id}/start`  
`/sd/{id}/mongos/{id}/stop`  
`/sd/{id}/mongos/{id}/restart`  
see [Host Object](#host-object-2)  

##### Shard Hosts #####
URI: `/sd/{id}/hosts`  
*Methods*:  
**GET** - return list of Cluster hosts  
*available response representations:*  
  + 200 - application/json 
  + 404 - Returned if the Cluster not exist  

Example:  

    {
      
    }


URI: `/sd/{id}/hs`  
see [Host](#hosts-1) Collection

URI: `/sd/{id}/hs/{id}`  
see [Host Object](#host-object-2)  


## Notes ##
