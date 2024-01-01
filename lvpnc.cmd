@echo off

PATH=%~dp0;%~dp0\bin;%~dp0\python;%PATH%
call %~dp0\virtualenv\scripts\activate.bat
pythonw %~dp0\client.py %1 %2 %3 %4 %5 %6 %7 %8 %9
