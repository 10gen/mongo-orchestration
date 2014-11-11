# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

param([string]$server, [string]$configuration, [string]$authentication="noauth", [string]$ssl="nossl", [string]$storage="mmapv1")

echo "-------------------------------------------------------"
echo "Server: $server"
echo "Configuration: $configuration"
echo "Authentication: $authentication"
echo "SSL: $ssl"
echo "Storage Engine: $storage"
echo "-------------------------------------------------------"

$BASEPATH_DOUBLEBACK=$env:BASEPATH -replace '\\','\\'

# Note: backslashes must be escaped in the following string:
$DATAPATH="$BASEPATH_DOUBLEBACK\\data"
# Note: backslashes must be escaped in the following string:
$SSL_FILES_ROOT="C:\\test-lib\\ssl-files"
# This environment variable is injected by Jenkins.
# Uncomment the following line to use this script outside of Jenkins:
# $WORKSPACE="C:\\mongo"
# Note: backslashes must be escaped in the following string:
$LOGPATH="$BASEPATH_DOUBLEBACK\\logs"

# Clean up files
$ErrorActionPreference = 'SilentlyContinue'
del -Recurse -Force $DATAPATH
del -Recurse -Force $LOGPATH
$ErrorActionPreference = 'Continue'

md "$($DATAPATH)\db27016"
md "$($DATAPATH)\db27017"
md "$($DATAPATH)\db27018"
md "$($DATAPATH)\db27019"
md "$LOGPATH"

# Needs to be distinct from "TEST_PARAMS" so we don't pass this to any mongos.
$STORAGE_PARAMS=""
if (($server -eq "22-release") -Or ($server -eq "20-release")) {
    $TEST_PARAMS='"vv" : true, '
} elseif ($server -eq "24-release") {
    $TEST_PARAMS='"setParameter" : {"enableTestCommands": 1, "textSearchEnabled": true}, "vv" : true, '
} elseif ($server -eq "27-nightly") {
    $TEST_PARAMS='"setParameter" : {"enableTestCommands": 1, "authenticationMechanisms": "MONGODB-CR,SCRAM-SHA-1"}, "vv" : true, '
    $STORAGE_PARAMS="`"storageEngine`": `"$storage`", "
} else {
    $TEST_PARAMS='"setParameter":{"enableTestCommands": 1}, "vv" : true, '
}

if ($authentication -eq "auth") {
    $AUTH_PARAMS='"login":"bob", "password": "pwd123", "auth_key": "secret",'
}

if ($ssl -eq "ssl") {
   echo "Using SSL"
   $SSL_PARAMS="`"sslParams`": {`"sslMode`": `"requireSSL`", `"sslAllowInvalidCertificates`" : true, `"sslPEMKeyFile`":`"$($SSL_FILES_ROOT)\\server.pem`", `"sslCAFile`": `"$($SSL_FILES_ROOT)\\ca.pem`", `"sslWeakCertificateValidation`" : true},"
}

echo "TEST_PARAMS=$TEST_PARAMS"
echo "AUTH_PARAMS=$AUTH_PARAMS"
echo "SSL_PARAMS=$SSL_PARAMS"
echo "STORAGE_PARAMS=$STORAGE_PARAMS"

echo "-------------------------------------------------------"
echo "MongoDB Configuration: $configuration"
echo "-------------------------------------------------------"

$http_request = New-Object -ComObject Msxml2.XMLHTTP
if ($configuration -eq "single_server") {
    $post_url = "http://localhost:8889/servers"
    $get_url = "http://localhost:8889/servers"
    $request_body="{$AUTH_PARAMS $SSL_PARAMS `"name`": `"mongod`", `"procParams`": {$TEST_PARAMS $STORAGE_PARAMS `"port`": 27017, `"dbpath`": `"$DATAPATH`", `"logpath`":`"$($LOGPATH)\\mongo.log`", `"ipv6`":true, `"logappend`":true, `"nojournal`":true}}"
} elseif ($configuration -eq "replica_set") {
    $post_url = "http://localhost:8889/replica_sets"
    $get_url = "http://localhost:8889/replica_sets/repl0"
    $request_body="{$AUTH_PARAMS $SSL_PARAMS `"id`": `"repl0`", `"members`":[{`"rsParams`":{`"priority`": 99, `"tags`":{ `"ordinal`": `"one`", `"dc`": `"ny`"}}, `"procParams`": {$TEST_PARAMS $STORAGE_PARAMS `"dbpath`":`"$($DATAPATH)\\db27017`", `"port`": 27017, `"logpath`":`"$($LOGPATH)\\db27017.log`", `"nojournal`":false, `"nohttpinterface`": true, `"noprealloc`":true, `"smallfiles`":true, `"nssize`":1, `"oplogSize`": 150, `"ipv6`": true}}, {`"rsParams`": {`"priority`": 1.1, `"tags`":{`"ordinal`": `"two`", `"dc`": `"pa`"}}, `"procParams`":{$TEST_PARAMS $STORAGE_PARAMS `"dbpath`":`"$($DATAPATH)\\db27018`", `"port`": 27018, `"logpath`":`"$($LOGPATH)\\db27018.log`", `"nojournal`":false, `"nohttpinterface`": true, `"noprealloc`":true, `"smallfiles`":true, `"nssize`":1, `"oplogSize`": 150, `"ipv6`": true}}, {`"procParams`":{`"dbpath`":`"$($DATAPATH)\\db27019`", `"port`": 27019, `"logpath`":`"$($LOGPATH)\\27019.log`", `"nojournal`":false, `"nohttpinterface`": true, `"noprealloc`":true, `"smallfiles`":true, `"nssize`":1, `"oplogSize`": 150, `"ipv6`": true}}]}" 
} elseif ($configuration -eq "sharded") {
    $post_url = "http://localhost:8889/sharded_clusters"
    $get_url = "http://localhost:8889/sharded_clusters/shard_cluster_1"
    $request_body = "{$AUTH_PARAMS $SSL_PARAMS `"routers`": [{$TEST_PARAMS `"port`": 27017, `"logpath`": `"$LOGPATH\\router27017.log`"}, {$TEST_PARAMS `"port`": 27018, `"logpath`": `"$LOGPATH\\router27018.log`"}], `"configsvrs`": [{`"port`": 27016, `"dbpath`": `"$DATAPATH\\db27016`", `"logpath`": `"$LOGPATH\\configsvr27016.log`"}], `"id`": `"shard_cluster_1`", `"shards`": [{`"id`": `"sh01`", `"shardParams`": {`"procParams`": {$TEST_PARAMS $STORAGE_PARAMS `"port`": 27020, `"dbpath`": `"$DATAPATH\\db27020`", `"logpath`":`"$LOGPATH\\db27020.log`", `"ipv6`":true, `"logappend`":true, `"nojournal`":false}}}]}" 
} else{
    echo "Unrecognized configuration: $configuration"
    exit 1
}
echo "Sending $request_body to $post_url"
$http_request.open('POST', $post_url, $false)
$http_request.setRequestHeader("Content-Type", "application/json")
$http_request.setRequestHeader("Accept", "application/json")
$http_request.send($request_body)
$response = $http_request.statusText

$get_request = New-Object -ComObject Msxml2.XMLHTTP
$get_request.open('GET', $get_url, $false)
$get_request.setRequestHeader("Accept", "application/json")
$get_request.send("")
echo $get_request.statusText
