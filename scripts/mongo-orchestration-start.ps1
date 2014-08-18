param([string]$configuration_file="mongo-orchestration-windows.config", [string]$server, [string]$python_bin="C:\\Python27\\python.exe")

echo "====== CLEANUP ======"
echo "*** Killing any existing MongoDB Processes which may not have shut down on a prior job."

# Cleanup code may raise errors if there are no such processes running, directories to remove, etc.
# Don't show these in the build log.
$ErrorActionPreference = 'SilentlyContinue'

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
del -Recurse -Force "$($env:BASEPATH)\data"
del -Recurse -Force "$($env:BASEPATH)\logs"

# Start caring about errors messages again.
$ErrorActionPreference = 'Continue'

echo "====== END CLEANUP ======"

echo "Copying mongo-orchestration to $env:WORKSPACE\mongo-orchestration"
copy-item -recurse D:\jenkins\mongo-orchestration $env:WORKSPACE\mongo-orchestration
cd $env:WORKSPACE\mongo-orchestration

echo "Start-Process -FilePath $python_bin -ArgumentList server.py,start,-f,$configuration_file,-e,$server,--no-fork"
Start-Process -FilePath $python_bin -ArgumentList server.py,start,-f,$($configuration_file),-e,$($server),--no-fork

$connected = $False
$ErrorActionPreference = 'SilentlyContinue'
echo "Waiting for Mongo Orchestration to become available..."
for ( $attempts = 0; $attempts -lt 1000 -and ! $connected; $attempts++ ) {
   $s = New-Object Net.Sockets.TcpClient
   $s.Connect("localhost", 8889)
   if ($s.Connected) {
      $connected = $True
   } else {
      Start-Sleep -m 100
   }
}
if (! $connected) {
   throw ("Could not connect to Mongo Orchestration.")
}
$ErrorActionPreference = 'Continue'
