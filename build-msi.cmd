pip install virtualenv
python -m virtualenv virtualenv
call .\virtualenv\Scripts\activate.bat

pip install -r requirements.txt
pyinstaller --clean --noconfirm --collect-submodules kivy_garden --collect-all kivy_garden.qrcode -w -r bin/lethean-wallet-rpc.exe -r bin/lethean-wallet-cli.exe --add-binary bin/lethean-wallet-rpc.exe:bin/lethean-wallet-rpc.exe --add-binary bin/lethean-wallet-rpc.exe:bin/lethean-wallet-cli.exe client.py
python setup.py bdist_wheel
