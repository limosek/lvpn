
$Env:PATH = ""
$version = "0.4"
$python_version = "3.12.1"
$lethean_version = "v5.0.1"
$lvpn_branch = "main"
$root = "${env:HOMEDRIVE}${env:HOMEPATH}\lvpn"

# Create LVPN home directory
if (-not (Test-Path "${root}"))
{
  mkdir "${root}"
}

# Create LVPN app directory
if (-not (Test-Path "${root}\app"))
{
  mkdir "${root}\app"
}
$appdir = "${root}\app"
$logfile = "${root}\setup.log"

Set-Location $app

if (-not (Test-Path "lvpn.zip"))
{
    Invoke-WebRequest "https://github.com/limosek/lvpn/archive/refs/heads/${lvpn_branch}.zip" -OutFile "lvpn.zip"
}
Expand-Archive python.zip -DestinationPath .

if (-not (Test-Path "lethean-cli-windows.zip"))
{
    Invoke-WebRequest "https://github.com/letheanVPN/blockchain-iz/releases/download/${lethean_version}/lethean-cli-windows.zip" -OutFile lethean-cli-windows.zip
}
Expand-Archive lethean-cli-windows.zip

if (-not (Test-Path "python.zip"))
{
    Invoke-WebRequest "https://www.python.org/ftp/python/${python_version}/python-${python_version}-embed-amd64.zip" -OutFile "python.zip"
}
Expand-Archive python.zip -DestinationPath python
Set-Location python
Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
.\python get-pip.py
@"
..
.\Lib
.\Lib\site-packages
import site
"@ | Out-File -Encoding utf8 -FilePath python312._pth -Append
.\python -m pip install virtualenv

$Env:PATH += ";" + (Resolve-Path .\python)
$Env:PATH += ";" + (Resolve-Path .\python\scripts)
$Env:PATH += ";" + (Resolve-Path .\bin)
$Env:PATH += ";" + (Resolve-Path .\lethean-cli-windows)

.\python\python -m pip install -r requirements.txt
