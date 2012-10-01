## Defined variables ##
+ **type** - type of collection
  + **rs** - ReplicaSet
  + **ms** - Master-Slave
  + **hs** - Hosts
+ **object_id** - object id
+ **property**  - object property
  + **primary**        - primary host
  + **secondaries**    - secondaries hosts
  + **arbiters**       - arbiters
  + **hosts**          - hosts
  + **hidden-members** - hidden members
+ **command**   - action to change object state
  + **start**   - get up host
  + **stop**    - stop host (data doesn't remove)
  + **restart** - restart host


## REST API ##

### Create object ###
    POST /{type}

### Change object state ##
    PUT /{type}/{object_id}/{command}

### Get object info ##
    GET /{type}/{object_id}

### Get value of object property ###
    GET /{type}/{object_id}/{property}

### Change object info ###
    PUT /{type}/{object_id}

### Change object property ###
    PUT /{type}/{object_id}/{property}

### Delete object ###
    DELETE /{type}/{object_id}


## Examples ##


### Stop host 232 in ReplicaSet 2323 in shard 12342 ###
    PUT /shard/12342/rs/2323/hs/232/stop


### Get all arbiters for ReplicaSet 123456
    GET /rs/123456/arbiters


### Remove host 23443 from Shard 344 from ReplicaSet rs-34543
    DELETE /shard/344/rs/rs-34543/hs/23443


## Notes ##
