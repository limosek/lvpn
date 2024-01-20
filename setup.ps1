
#Set-PSDebug -Trace 1
$ErrorActionPreference = "Inquire"

if (-not (Test-Path "${env:HOMEDRIVE}${env:HOMEPATH}\lvpn"))
{
  mkdir "${env:HOMEDRIVE}${env:HOMEPATH}\lvpn"
}
$root = "${env:LOCALAPPDATA}\lvpn"
Set-Location $root
$logfile = "${env:HOMEDRIVE}${env:HOMEPATH}\lvpn\setup.log"

$Env:PATH += ";" + (Resolve-Path .\python)
$Env:PATH += ";" + (Resolve-Path .\python\scripts)
$Env:PATH += ";" + (Resolve-Path .\bin)

.\python\python -m pip install -r requirements.txt 2>&1 >>$logfile

