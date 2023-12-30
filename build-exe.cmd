pip install virtualenv
python -m virtualenv virtualenv
call .\virtualenv\Scripts\activate.bat

pip install -r requirements.txt --pre --extra-index-url https://kivy.org/downloads/simple/

pyinstaller --clean --noconfirm -i config/icon.ico --collect-submodules kivy_garden --collect-all kivy_garden.qrcode -w --add-binary bin/lethean-wallet-rpc.exe:bin/ --add-binary bin/lethean-wallet-cli.exe:bin/ --add-data config:config client.py
pyinstaller --clean --noconfirm -c ptwbin.py
copy dist\ptwbin\ptwbin.exe dist\client\ptw.exe

powershell .\build-msi.ps1
del dist\lvpn*.zip
powershell Compress-Archive dist\client dist\lvpn-0.1.zip
