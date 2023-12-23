pip install virtualenv
rd /s /q virtualenv
python -m virtualenv virtualenv --relocatable
call .\virtualenv\Scripts\activate.bat

pip install -r requirements.txt
#pyinstaller --clean --noconfirm --hidden-import kivy_garden -w -r bin/lethean-wallet-rpc.exe -r bin/lethean-wallet-cli.exe --add-binary bin/lethean-wallet-rpc.exe:bin/lethean-wallet-rpc.exe --add-binary bin/lethean-wallet-rpc.exe:bin/lethean-wallet-cli.exe --collect-all kivy client.py
python setup.py bdist_wheel



