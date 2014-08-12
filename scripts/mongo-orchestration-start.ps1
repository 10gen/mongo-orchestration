param([string]$configuration_file="mongo-orchestration-windows.config", [string]$release, [string]$python_bin="C:\\Python27\\python.exe", [string]$git_branch="master")

$BASE_PATH="C:\mongo"

echo "====== CLEANUP ======"
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

echo "remove old files from $BASE_PATH"
del -Recurse -Force "$($BASE_PATH)\data"
del -Recurse -Force "$($BASE_PATH)\logs"
echo "====== END CLEANUP ======"

git clone https://github.com/mongodb/mongo-orchestration.git --branch $git_branch --depth 1
cd mongo-orchestration

echo "Start-Process -FilePath $python_bin -ArgumentList server.py,start,-f,$configuration_file,-e,$release,--no-fork"
Start-Process -FilePath $python_bin -ArgumentList server.py,start,-f,$configuration_file,-e,$release,--no-fork
