call .\virtualenv\Scripts\activate.bat

rem pyinstaller --clean --noconfirm -w -r bin/lethean-wallet-rpc.exe --add-binary bin/lethean-wallet-rpc.exe:bin/lethean-wallet-rpc.exe -F client.py
python setup.py bdist_msi


