if [ "$1" ]; then
    python_bin=$1
else
    python_bin=/usr/bin/python
fi

cd $WORKSPACE/mongo-orchestration
$python_bin server.py stop

echo "====== CLEANUP ======"
echo "*** Killing any existing MongoDB Processes which may not have shut down on a prior job."
PSES=`ps auxwwww | grep "mongod" | grep -v grep | awk {'print \$2'}`
echo "about to kill the following: `ps auxwwww | grep "mongod" | grep -v grep`"
echo "Found existing mongod Processes: $PSES"
for x in $PSES
do
    echo "Killing MongoD at $x"
    kill -9 $x
done

PSES=`ps auxwwww | grep "mongos" | grep -v grep | awk {'print \$2'}`
echo "about to kill the following: `ps auxwwww | grep "mongos" | grep -v grep`"
echo "Found existing mongos Processes: $PSES"
for x in $PSES
do
    echo "Killing MongoD at $x"
    kill -9 $x
done


PSES=`ps auxwwww | grep "server.py " | grep -v grep | awk {'print \$2'}`
echo "about to kill the following: `ps auxwwww | grep "server.py" | grep -v grep`"
echo "Found existing mongo-orchestration Processes: $PSES"

for x in $PSES
do
    echo "Killing mongo-orchestration process at $x"
    kill -9 $x
done
echo "remove old files"
rm -rf /tmp/mongo-*
rm -f /tmp/test-*
du -sh /tmp

echo "====== END CLEANUP ======"
