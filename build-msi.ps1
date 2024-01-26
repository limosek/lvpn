# Basic variables
$Env:PATH = ""
$version = "0.4"
$python_version = "3.12.1"
$lethean_version = "v5.0.1"

# Cleanup
Remove-Item dist\msi -Recurse -Force
Remove-Item dist\lvpn -Recurse -Force

# Basic creation of dirs
mkdir dist
mkdir dist/lvpn
mkdir dist/lvpn/python
Set-Location dist

# Stop on any error
$ErrorActionPreference = "Stop"

if (-not (Test-Path "python.zip"))
{
    Invoke-WebRequest "https://www.python.org/ftp/python/${python_version}/python-${python_version}-embed-amd64.zip" -OutFile "python.zip"
}
Expand-Archive python.zip -DestinationPath lvpn/python
Set-Location lvpn/python
Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
.\python get-pip.py
@"
..
.\Lib
.\Lib\site-packages
import site
"@ | Out-File -Encoding utf8 -FilePath python312._pth -Append
.\python -m pip install virtualenv

Set-Location ..
mkdir bin

$Env:PATH += ";" + (Resolve-Path .\python)
$Env:PATH += ";" + (Resolve-Path .\bin)

Copy-Item ../../*py ./
Copy-Item ../../*cmd ./
Copy-Item ../../*ps1 ./
Copy-Item ../../requirements* ./
Copy-Item -Recurse ../../lib ./
Copy-Item -Recurse ../../server ./
Copy-Item -Recurse ../../client ./
Copy-Item -Recurse ../../config ./

Set-Location ..
if (-not (Test-Path "lethean-cli-windows.zip"))
{
    Invoke-WebRequest "https://github.com/letheanVPN/blockchain-iz/releases/download/${lethean_version}/lethean-cli-windows.zip" -OutFile lethean-cli-windows.zip
}
Expand-Archive lethean-cli-windows.zip
Copy-Item lethean-cli-windows\lethean-cli-windows\lethean-wallet-rpc.exe lvpn/bin/
Copy-Item lethean-cli-windows\lethean-cli-windows\lethean-wallet-cli.exe lvpn/bin/
#Copy-Item lethean-cli-windows\lethean-cli-windows\letheand.exe lvpn/bin/
Copy-Item lethean-cli-windows\lethean-cli-windows\lib* lvpn/bin/
Remove-Item lethean-cli-windows -Recurse

function addDir {
  param (
        [string]$dir,
        [string]$toplevel
  )

  write-host "addDir $dir"
  $mydir = (split-path -leaf $dir)

  New-InstallerDirectory -DirectoryName $mydir -Content {
      if ($toplevel -eq "1") {
           New-InstallerFile $dir\lvpnc.cmd -Id "mainFile"
           New-InstallerFile $dir\lvpnc-debug.cmd -Id "mainFileDbg"
           New-InstallerFile $dir\client.py -Id "clientPy"
           New-InstallerFile $dir\server.py -Id "serverPy"
           New-InstallerFile $dir\mgmt.py -Id "mgmtPy"
           New-InstallerFile $dir\setup.ps1 -Id "setupscript"
           New-InstallerFile $dir\requirements.txt -Id "reqs"
      } else {
          Get-ChildItem $dir -file -Recurse -Depth 0 | ForEach-Object { write-host "addFile: $dir/$_"; New-InstallerFile $dir/$_ }
      }
      Get-ChildItem $dir -directory -Recurse -Depth 0 | split-path -Leaf | ForEach-Object { addDir $dir/$_ }
  }
}

$setup = New-InstallerCustomAction -FileId 'setupscript' -RunOnInstall -CheckReturnValue
New-Installer -ProductName "LVPN" -Manufacturer "Lethean.Space" -ProductId "672fe9ec-7d23-4d80-a194-fabe5dcc4dc6" -UpgradeCode '111a932a-b7dc-4276-a42c-241250f33483' -Version ${version} -Content {
    New-InstallerDirectory -PredefinedDirectory "LocalAppDataFolder"  -Content {
        addDir lvpn 1
        New-InstallerDirectory -PredefinedDirectory "DesktopFolder" -Content {
            New-InstallerShortcut -Name "LVPN" -FileId "mainFile" -IconPath "$pwd\..\config\lvpn.ico"
            New-InstallerShortcut -Name "LVPN-Debug" -FileId "mainFileDbg" -IconPath "$pwd\..\config\lvpn.ico"
        }
    }
 } -OutputDirectory (Join-Path $pwd "msi") -AddRemoveProgramsIcon "$pwd\..\config\lvpn.ico" -CustomAction $setup

Get-FileHash msi\lvpn.${version}.x86.msi
