pip install virtualenv
python -m virtualenv virtualenv
call .\virtualenv\Scripts\activate.bat

pip install -r requirements.txt --pre --extra-index-url https://kivy.org/downloads/simple/

pyinstaller --clean --noconfirm -i config/icon.ico --collect-submodules kivy_garden --collect-all kivy_garden.qrcode -c --add-binary bin/lethean-wallet-rpc.exe:bin/ --add-binary bin/lethean-wallet-cli.exe:bin/ --add-data config:config client.py

cd dist
powershell ..\build-msi.ps1
