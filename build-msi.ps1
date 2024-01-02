$Env:PATH = ""
mkdir dist
mkdir dist/lvpn
mkdir dist/lvpn/python
Set-Location dist

if (-not (Test-Path "python.zip"))
{
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.1/python-3.12.1-embed-amd64.zip" -OutFile "python.zip"
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
.\python -m pip install venv
.\python -m venv ../virtualenv
. ..\virtualenv\Scripts\activate.ps1

Set-Location ..
mkdir bin

$Env:PATH += ";" + (Resolve-Path .\python)
$Env:PATH += ";" + (Resolve-Path .\virtualenv\scripts)
$Env:PATH += ";" + (Resolve-Path .\bin)

python -m pip install kivy --pre --no-deps --index-url  https://kivy.org/downloads/simple/
python -m pip install "kivy[base]" --pre --extra-index-url https://kivy.org/downloads/simple/
python -m pip install -r ..\..\requirements.txt

Copy-Item ../../*py ./
Copy-Item ../../*cmd ./
Copy-Item ../../*ps1 ./
Copy-Item -Recurse ../../lib ./
Copy-Item -Recurse ../../server ./
Copy-Item -Recurse ../../client ./
Copy-Item -Recurse ../../config ./

Set-Location ..
if (-not (Test-Path "lethean-cli-windows.zip"))
{
    Invoke-WebRequest "https://github.com/letheanVPN/blockchain-iz/releases/download/v5.0.1/lethean-cli-windows.zip" -OutFile lethean-cli-windows.zip
}
Expand-Archive lethean-cli-windows.zip
Copy-Item lethean-cli-windows\lethean-cli-windows\lethean-wallet-rpc.exe lvpn/bin/
Copy-Item lethean-cli-windows\lethean-cli-windows\lethean-wallet-cli.exe lvpn/bin/
#Copy-Item lethean-cli-windows\lethean-cli-windows\letheand.exe lvpn/bin/
Copy-Item lethean-cli-windows\lethean-cli-windows\lib* lvpn/bin/
python client.py
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
           New-InstallerFile $dir\ptwbin.py -Id "ptwPy"
           New-InstallerFile $dir\setup.ps1 -Id "setupscript"
      } else {
          Get-ChildItem $dir -file -Recurse -Depth 0 | ForEach-Object { write-host "addFile: $dir/$_"; New-InstallerFile $dir/$_ }
      }
    Get-ChildItem $dir -directory -Recurse -Depth 0 | split-path -Leaf | ForEach-Object { addDir $dir/$_ }
  }
}

New-Installer -ProductName "LVPN" -Manufacturer "Lethean.Space" -ProductId "672fe9ec-7d23-4d80-a194-fabe5dcc4dc6" -UpgradeCode '111a932a-b7dc-4276-a42c-241250f33483' -Version 0.3 -Content {
    New-InstallerDirectory -PredefinedDirectory "LocalAppDataFolder"  -Content {
        addDir lvpn 1
        New-InstallerDirectory -PredefinedDirectory "DesktopFolder" -Content {
            New-InstallerShortcut -Name "LVPN" -FileId "mainFile" -IconPath "$pwd\..\config\icon.ico"
            New-InstallerShortcut -Name "LVPN-Debug" -FileId "mainFileDbg" -IconPath "$pwd\..\config\icon.ico"
        }
    }
    New-InstallerCustomAction -FileId 'setupscript' -RunOnInstall
 } -OutputDirectory (Join-Path $pwd "msi") -AddRemoveProgramsIcon "$pwd\..\config\icon.ico"

mkdir zip
Compress-Archive -Path .\lvpn -DestinationPath zip\lvpn-0.3.zip
