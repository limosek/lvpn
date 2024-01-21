@echo off

PATH="%~dp0\python\scripts;%~dp0;%~dp0\lethean-cli-windows;%~dp0\python;%PATH%"
.\python\python.exe "%~dp0\client.py" %1 %2 %3 %4 %5 %6 %7 %8 %9
