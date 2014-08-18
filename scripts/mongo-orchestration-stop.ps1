param([string]$python_bin="C:\\Python27\\python.exe")

cd $env:WORKSPACE\mongo-orchestration
& $python_bin server.py stop

echo "====== CLEANUP ======"

# Cleanup code may raise errors if there are no such processes running, directories to remove, etc.
# Don't show these in the build log.
$ErrorActionPreference = 'SilentlyContinue'

echo "*** Killing any existing MongoDB Processes which may not have shut down on a prior job."
$mongods = (Get-Process mongod)
echo "Found existing mongod Processes: $mongods"
$mongoss = (Get-Process mongos)
echo "Found existing mongos Processes: $mongoss"
Stop-Process -InputObject $mongods
Stop-Process -InputObject $mongoss

$pythons = (Get-Process python)
foreach ($python in $pythons) {
    $procid = $python.id
    $wmi = (Get-WmiObject Win32_Process -Filter "Handle = '$procid'")
    if ($wmi.CommandLine -like "*server.py*") {
	Stop-Process -id $wmi.Handle
    }
}

echo "remove old files from $env:BASEPATH"
del -Recurse -Force $env:BASEPATH\data
del -Recurse -Force $env:BASEPATH\logs
echo "====== END CLEANUP ======"

# Start caring about errors messages again.
$ErrorActionPreference = 'Continue'
