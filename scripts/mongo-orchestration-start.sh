echo "====== CLEANUP ======"
echo "*** Killing any existing MongoDB Processes which may not have shut down on a prior job."
PSES=`ps auxwwww | grep "mongod" | grep -v grep | awk {'print \$2'}`
echo "Found existing mongod Processes: $PSES"
for x in $PSES
do
    echo "Killing MongoD at $x"
    kill -9 $x
done

PSES=`ps auxwwww | grep "mongos" | grep -v grep | awk {'print \$2'}`
echo "Found existing mongos Processes: $PSES"
for x in $PSES
do
    echo "Killing MongoD at $x"
    kill -9 $x
done


PSES=`ps auxwwww | grep "server.py " | grep -v grep | awk {'print \$2'}`
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


if [ "$1" ]; then
    config_file=$1
else
    config_file=mongo-orchestration.config
fi

if [ "$2" ]; then
    release=$2
else
    release="stable-release"
fi

if [ "$3" ]; then
    python_bin=$3
else
    python_bin=/usr/bin/python
fi

if [ "$4" ]; then
    git_branch=$4
else
    git_branch=jenkins
fi

rm -rf mongo-orchestration

git clone git@github.com:mongodb/mongo-orchestration.git --branch $git_branch --depth 1
cd mongo-orchestration
#cat $config_file
# git checkout jenkins
echo $python_bin server.py start -f $config_file -e $2
$python_bin server.py start -f $config_file -e $2
