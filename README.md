# REST API to manage mongos instances #

## Defined terms ##

### Type of Collections ###
+ **hs** - Hosts
+ **rs** - ReplicaSet (each *rs* contains one *hs* collection)
+ **ms** - Master-Slave (each *ms* contains one *hs* collection)

ReplicaSet *rs* and Master-Slave *ms* collections should contains Hosts *hs* collection

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
[http://localhost:8888/rest/api/latest/hs](#hosts-1) [POST]  
#### Host Object ####
[http://localhost:8888/rest/api/latest/hs/{id}](#host-object-2) [GET, PUT, DELETE]  
[http://localhost:8888/rest/api/latest/hs/{id}/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/hs/{id}/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/hs/{id}/restart](#host-object-2) [PUT]  

### Master-Slave ###
[http://localhost:8888/rest/api/latest/ms](#master-slave-1) [POST]  
[http://localhost:8888/rest/api/latest/ms/{id}](#master-slave-1) [GET, PUT, DELETE]  
[http://localhost:8888/rest/api/latest/ms/{id}/hs](#master-slave-1) [HOSTS]  

### ReplicaSet ###
[http://localhost:8888/rest/api/latest/rs](#replicaset-1) [POST]  
[http://localhost:8888/rest/api/latest/rs/{id}](#replicaset-1) [GET, PUT, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/hosts](#replicaset-1) [GET]  
[http://localhost:8888/rest/api/latest/rs/{id}/hs](#rs-hosts) [POST]  
[http://localhost:8888/rest/api/latest/rs/{id}/hs/{id}](#host-object-2) [GET, PUT, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/hs/{id}/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hs/{id}/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hs/{id}/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/primary](#rs-primary) [GET, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/primary/stepdown](#rs-primary) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/primary/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/primary/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/primary/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries](#rs-secondaries) [GET, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/random](#rs-secondaries) [GET]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/random/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/random/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/random/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/{id}/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/{id}/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/secondaries/{id}/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters](#rs-arbiters) [GET, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/random](#rs-arbiters) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/random/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/random/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/random/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/{id}/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/{id}/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/arbiters/{id}/restart](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hidden](#rs-hidden) [GET, DELETE]  
[http://localhost:8888/rest/api/latest/rs/{id}/hidden/random](#rs-hidden) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hidden/random/start](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hidden/random/stop](#host-object-2) [PUT]  
[http://localhost:8888/rest/api/latest/rs/{id}/hidden/random/restart](#host-object-2) [PUT]  


## REST API RESOURCES ##
### Hosts ###
URI: `/hs`  
*Methods*:  
**POST** - create and get up new host   

##### Host Object #####
URI: `/hs/{id}`  
*Methods*:  
**GET**     - return info about host  
**PUT**     - change host state  
**DELETE**  - remove host with all data (log file, db files, ...)  

URI: `/hs/{id}/start`  
*Methods*:  
**PUT** - get up host  

URI: `/hs/{id}/stop`  
*Methods*:  
**PUT**  - stop host (data files don't remove)  

URI: `/hs/{id}/restart`  
*Methods*:  
**PUT** - restart host  

### Master-Slave ###
URI: `/ms`  
*Methods*:  
**POST** - create new Master-Slave configuration  

URI: `/ms/{id}`  
*Methods*:  
**GET** - return info about Master-Slave configuration  
**PUT** - change Master-Slave state  
**DELETE** - remove Master-Slave configuration  

##### MS Hosts #####
URI: `/ms/{id}/hs`  
see [HOSTS](#hosts-2) Collection

URI: `/ms/{id}/hs/{id}`  
see [HOST OBJECT](#host-object-2)  

### ReplicaSet ###
URI: `/rs`  
*Methods*:  
**POST** - create and get up new ReplicaSet  

URI: `/rs/{id}`  
*Methods*:  
**GET** - return info about ReplicaSet object  
**PUT** - change ReplicaSet state   
**DELETE** - remove ReplicaSet  

##### RS Hosts #####
URI: `/rs/{id}/hosts`  
*Methods*:  
**GET** - return list of ReplicaSets hosts  

URI: `/rs/{id}/hs`  
see [HOSTS](#hosts-2) Collection

URI: `/rs/{id}/hs/{id}`  
see [HOST OBJECT](#host-object-2)  

##### RS Primary #####
URI: `/rs/{id}/primary`  
*Methods*:  
**GET** - return primary host of ReplicaSet  
**DELETE** - remove primary host of ReplicaSet   

URI: `/rs/{id}/primary/stepdown`  
*Methods*:  
**PUT** - forces the primary of the replica set to relinquish its status as primary  

`/rs/{id}/primary/start`  
`/rs/{id}/primary/stop`  
`/rs/{id}/primary/restart`  
see [HOST OBJECT](#host-object-2)  

##### RS Secondaries #####
URI: `/rs/{id}/secondaries`  
*Methods*:  
**GET** - returl list of secondaries hosts  
**DELETE** - remove all secondaries hosts   

URI: `/rs/{id}/secondaries/random`  
*Methods*:  
**GET** - return random [HOST OBJECT](#host-object-2) from secondaries  

URI: `/rs/{id}/secondaries/{id}`  
*Methods*:  
**GET** -return [HOST OBJECT](#host-object-2) from secondaries  

##### RS Arbiters #####
URI: `/rs/{id}/arbiters`  
*Methods*:  
**GET** - return list of all arbiters for ReplicaSet  
**DELETE** - remove all ReplicaSets arbiters   

URI: `/rs/{id}/arbiters/random`  
*Methods*:  
**GET** -return random [HOST OBJECT](#host-object-2) from arbiters  

URI: `/rs/{id}/arbiters/{id}`  
*Methods*:  
**GET** -return [HOST OBJECT](#host-object-2) from arbiters  

##### RS Hidden #####
URI: `/rs/{id}/hidden`  
*Methods*:  
**GET** - returl list of all hidden hosts from ReplicaSet  
**DELETE** - remove all hidden hosts from ReplicaSet   

URI: `/rs/{id}/hidden/random`  
*Methods*:  
**GET** - return random [HOST OBJECT](#host-object-2) from hidden  


## Notes ##
