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

echo "Creating virtualenv"
del -Recurse -Force D:\jenkins\mo_env
C:\Python27\Scripts\virtualenv.exe D:\jenkins\mo_env
echo "Activating virtual environment"
D:\jenkins\mo_env\Scripts\activate.ps1
cd $WORKSPACE
echo "Start-Process -FilePath mongo-orchestration.exe -ArgumentList start,-f,$configuration_file,-e,$server,--no-fork"
Start-Process -FilePath mongo-orchestration.exe -ArgumentList start,-f,$($configuration_file),-e,$($server),--no-fork
echo "Sleeping 5 seconds to allow some time for Mongo Orchestration to start..."
Start-Sleep -s 5
