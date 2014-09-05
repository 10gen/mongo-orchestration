# mongo-orchestration-setup.sh
#
# Set up a MongoDB configuration on Jenkins. This script should be run only
# after server.py has started.
#
# Arguments:
# ----------
# 1. release (as defined in the --config file to server.py) [required]
# 2. configuration (single_server|replica_set|sharded) [required]
# 3. authentication (auth|noauth) [optional: defaults to "noauth"]
# 4. ssl (ssl|nossl) [optional: defaults to "nossl"]
#
# Influential environment variables:
# ----------------------------------
# + BASEPATH    Root directory in which to place log and data directories.
#               Defaults to "/mnt/jenkins".

BASEPATH=${BASEPATH:-/mnt/jenkins}
export BASEPATH
echo "BASEPATH=$BASEPATH"

rm -rf ${BASEPATH}/data/*

# builds are sometimes failing because the log dir doesn't exist.
mkdir -p ${BASEPATH}/log
mkdir -p ${BASEPATH}/data/db27017
mkdir -p ${BASEPATH}/data/db27018
mkdir -p ${BASEPATH}/data/db27019
cd ${BASEPATH}/data

echo "-------------------------------------------------------"
echo "Server: $1"
echo "Configuration: $2"
echo "Authentication: $3"
echo "SSL: $4"
echo "-------------------------------------------------------"

if [ "$1" == "22-release" -o "$1" == "20-release" ]; then
    TEST_PARAMS='"vv" : true, '
elif [ "$1" == "24-release" ]; then
    TEST_PARAMS='"setParameter" : {"textSearchEnabled" : true}, "vv" : true, '
else
    TEST_PARAMS='"setParameter": {"enableTestCommands" : 1}, "vv" : true, '
fi

if [ "$3" == "auth" ]; then
    AUTH_PARAMS='"login":"bob", "password": "pwd123", "auth_key": "secret",'
else
    AUTH_PARAMS=""
fi

if [ "$4" == "ssl" ]; then
    echo "Using SSL"
    export SSL_PARAMS='"sslParams": {"sslMode": "requireSSL", "sslAllowInvalidCertificates" : true, "sslPEMKeyFile":"/mnt/jenkins/mongodb/ssl/ssl-files/server.pem", "sslCAFile": "/mnt/jenkins/mongodb/ssl/ssl-files/ca.pem", "sslWeakCertificateValidation" : true},'
else
    export SSL_PARAMS=""
fi

export DATAPATH="${BASEPATH}/data"
export LOGPATH="${BASEPATH}/log"

echo "TEST_PARAMS=$TEST_PARAMS"
echo "AUTH_PARAMS=$AUTH_PARAMS"
echo "SSL_PARAMS=$SSL_PARAMS"
echo "DATAPATH=$DATAPATH"
echo "LOGPATH=$LOGPATH"
mkdir -p "$LOGPATH"

echo "-------------------------------------------------------"
echo "MongoDB Configuration: $2"
echo "-------------------------------------------------------"

date
if [ "$2" == "single_server" ]; then
    echo curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"name\": \"mongod\", \"procParams\": {$TEST_PARAMS \"port\": 27017, \"dbpath\": \"$DATAPATH\", \"logpath\":\"$LOGPATH/mongo.log\", \"ipv6\":true, \"logappend\":true, \"nojournal\": true}}" http://localhost:8889/servers
    curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"name\": \"mongod\", \"procParams\": { $TEST_PARAMS \"port\": 27017, \"dbpath\": \"$DATAPATH\", \"logpath\":\"$LOGPATH/mongo.log\", \"ipv6\":true, \"logappend\":true, \"nojournal\": true}}" http://localhost:8889/servers
    echo curl -i -H "Accept: application/json" -X GET http://localhost:8889/servers
    curl -f -i -H "Accept: application/json" -X GET http://localhost:8889/servers

elif [ "$2" == "replica_set" ]; then
    
    echo curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"id\": \"repl0\", \"members\":[{\"rsParams\":{\"priority\": 99}, \"procParams\": {$TEST_PARAMS \"dbpath\":\"$DATAPATH/db27017\", \"port\": 27017, \"logpath\":\"$LOGPATH/\
db27017.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}, {\"rsParams\": {\"priority\": 1.1}, \"procParams\":{$TEST_PARAMS \"dbpath\":\
\"$DATAPATH/db27018\", \"port\": 27018, \"logpath\":\"$LOGPATH/db27018.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}, \
{\"procParams\":{$TEST_PARAMS \"dbpath\":\"$DATAPATH/db27019\", \"port\": 27019, \"logpath\":\"$LOGPATH/27019.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}]}" http://localhost:8889/replica_sets
    curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"id\": \"repl0\", \"members\":[{\"rsParams\":{\"priority\": 99}, \"procParams\": {$TEST_PARAMS \"dbpath\":\"$DATAPATH/db27017\", \"port\": 27017, \"logpath\":\"$LOGPATH/db270\
17.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}, {\"rsParams\": {\"priority\": 1.1}, \"procParams\":{$TEST_PARAMS \"dbpath\":\"$DA\
TAPATH/db27018\", \"port\": 27018, \"logpath\":\"$LOGPATH/db27018.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}, {\"pr\
ocParams\":{\"dbpath\":\"$DATAPATH/db27019\", \"port\": 27019, \"logpath\":\"$LOGPATH/27019.log\", \"nojournal\": true, \"nohttpinterface\": true, \"noprealloc\":true, \"smallfiles\":true, \"nssize\":1, \"oplogSize\": 150, \"ipv6\": true}}]}" http://localhost:8889/replica_sets
    echo curl -i -H "Accept: application/json" -X GET http://localhost:8889/replica_sets/repl0/primary
    curl -f -i -H "Accept: application/json" -X GET http://localhost:8889/replica_sets/repl0/primary

elif [ "$2" == "sharded" ]; then
    echo curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"routers\": [{$TEST_PARAMS \"port\": 27017, \"logpath\": \"$LOGPATH/router27017.log\"}], \"configsvrs\": [{\"port\": 27016, \"dbpath\": \"$DATAPATH/db27016\", \"logpath\": \"$LOGPATH/configsvr27016.log\"}], \"id\": \"shard_cluster_1\", \"shards\": [{\"id\": \"sh01\", \"shardParams\": {\"procParams\": {$TEST_PARAMS \"port\": 27020, \"dbpath\": \"$DATAPATH/db27020\", \"logpath\":\"$LOGPATH/db27020.log\", \"ipv6\":true, \"logappend\":true, \"nojournal\": true}}}]}" http://127.0.0.1:8889/sharded_clusters
    curl -i -H "Accept: application/json" -X POST -d "{$AUTH_PARAMS $SSL_PARAMS \"routers\": [{$TEST_PARAMS \"port\": 27017, \"logpath\": \"$LOGPATH/router27017.log\"}], \"configsvrs\": [{\"port\": 27016, \"dbpath\": \"$DATAPATH/db27016\", \"logpath\": \"$LOGPATH/configsvr27016.log\"}], \"id\": \"shard_cluster_1\", \"shards\": [{\"id\": \"sh01\", \"shardParams\": {\"procParams\": {$TEST_PARAMS \"port\": 27020, \"dbpath\": \"$DATAPATH/db27020\", \"logpath\":\"$LOGPATH/db27020.log\", \"ipv6\":true, \"logappend\":true, \"nojournal\": true}}}]}" http://127.0.0.1:8889/sharded_clusters
    echo curl -f -i -H "Accept: application/json" -X GET http://localhost:8889/sharded_clusters/shard_cluster_1
    curl -f -i -H "Accept: application/json" -X GET http://localhost:8889/sharded_clusters/shard_cluster_1

fi
