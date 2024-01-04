
@"
home = ${env:LOCALAPPDATA}\lvpn\python
implementation = CPython
version_info = 3.12.1.final.0
virtualenv = 20.25.0
include-system-site-packages = false
base-prefix = ${env:LOCALAPPDATA}\lvpn\python
base-exec-prefix = ${env:LOCALAPPDATA}\lvpn\python
base-executable = ${env:LOCALAPPDATA}\lvpn\python\python.exe
"@ | Out-File -Encoding utf8 -FilePath ${env:LOCALAPPDATA}\lvpn\virtualenv\pyvenv.cfg

mkdir ${env:HOMEDRIVE}${env:HOMEPATH}\lvpn
