PATH=%~dp0;%~dp0\bin;%~dp0\python;%PATH%
call %~dp0\virtualenv\scripts\activate.bat
%~dp0\virtualenv\scripts\python %~dp0\client.py -l DEBUG %1 %2 %3 %4 %5 %6 %7 %8 %9
