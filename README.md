# LVPN

Blockchain powered VPN for sharing and anonymity with decentralisation.
See [Homepage](https://lethean.space)

## Installation
Installation does not need admin privileges.
See [Install guide](https://lethean.space/client-install)

## Support
Use GitHub issue tracker. You can earn coins by reporting bugs! 

## I want to donate development!
Great! We will do our best to make software great!
See [Possibiliies](https://lethean.space)

## Contributing
Do you want to contribute? Create a pull request!  You can earn coins by creating pull request!

## License
GPLv3

## Client

Client part is multiplatform and can run with or without GUI.
```commandline
usage: client.py [-h] [-c CONFIG] [--ptw-bin PTW_BIN] [--wallet-rpc-bin WALLET_RPC_BIN] [--wallet-cli-bin WALLET_CLI_BIN] [--daemon-rpc-bin DAEMON_RPC_BIN] [-l {DEBUG,INFO,WARNING,ERROR}] [--spaces-dir SPACES_DIR]
                 [--gates-dir GATES_DIR] [--authids-dir AUTHIDS_DIR] [--coin-type {lethean,monero}] [--coin-unit COIN_UNIT] [--run-gui {0,1}] [--run-proxy {0,1}] [--run-wallet {0,1}] [--run-daemon {0,1}]
                 [--chromium-bin CHROMIUM_BIN] [--daemon-host DAEMON_HOST] [--daemon-p2p-port DAEMON_P2P_PORT] [--daemon-rpc-url DAEMON_RPC_URL] [--wallet-rpc-url WALLET_RPC_URL] [--wallet-rpc-port WALLET_RPC_PORT]
                 [--wallet-rpc-user WALLET_RPC_USER] [--wallet-rpc-password WALLET_RPC_PASSWORD] [--wallet-name WALLET_NAME] [--wallet-password WALLET_PASSWORD]
                 [cmd ...]

positional arguments:
  cmd                   Choose command

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Config file path
  --ptw-bin PTW_BIN
  --wallet-rpc-bin WALLET_RPC_BIN
                        Wallet RPC binary file
  --wallet-cli-bin WALLET_CLI_BIN
                        Wallet CLI binary file
  --daemon-rpc-bin DAEMON_RPC_BIN
                        Daemon binary file
  -l {DEBUG,INFO,WARNING,ERROR}
                        Log level [env var: WLC_LOGLEVEL]
  --spaces-dir SPACES_DIR
                        Directory containing all spaces SDPs
  --gates-dir GATES_DIR
                        Directory containing all gateway SDPs
  --authids-dir AUTHIDS_DIR
                        Directory containing all authids
  --coin-type {lethean,monero}
                        Coin type to sue [env var: WLC_COINTYPE]
  --coin-unit COIN_UNIT
                        Coin minimal unit
  --run-gui {0,1}       Run GUI
  --run-proxy {0,1}     Run local proxy
  --run-wallet {0,1}    Run local wallet
  --run-daemon {0,1}    Run local daemon RPC
  --chromium-bin CHROMIUM_BIN
                        Chromium browser binary
  --daemon-host DAEMON_HOST
                        Daemon host
  --daemon-p2p-port DAEMON_P2P_PORT
                        Daemon P2P port
  --daemon-rpc-url DAEMON_RPC_URL
                        Daemon RPC URL
  --wallet-rpc-url WALLET_RPC_URL
                        Wallet RPC URL
  --wallet-rpc-port WALLET_RPC_PORT
                        Wallet RPC port
  --wallet-rpc-user WALLET_RPC_USER
                        Wallet RPC user
  --wallet-rpc-password WALLET_RPC_PASSWORD
                        Wallet RPC password. Default is to generate random
  --wallet-name WALLET_NAME
                        Wallet name
  --wallet-password WALLET_PASSWORD
                        Wallet password

Args that start with '--' can also be set in a config file (/etc/lvpn/client.ini or C:\Users\lukas/lvpn//client.ini or C:\Users\lukas/lvpn//client.ini or specified via -c). Config file syntax allows: key=value, flag=true,
stuff=[a,b,c] (for details, see syntax at https://goo.gl/R74nmi). In general, command-line values override environment variables which override config file values which override defaults.
Bad configuration or commandline argument.
usage: client.py [-h] [-c CONFIG] [--ptw-bin PTW_BIN] [--wallet-rpc-bin WALLET_RPC_BIN] [--wallet-cli-bin WALLET_CLI_BIN] [--daemon-rpc-bin DAEMON_RPC_BIN] [-l {DEBUG,INFO,WARNING,ERROR}] [--spaces-dir SPACES_DIR]
                 [--gates-dir GATES_DIR] [--authids-dir AUTHIDS_DIR] [--coin-type {lethean,monero}] [--coin-unit COIN_UNIT] [--run-gui {0,1}] [--run-proxy {0,1}] [--run-wallet {0,1}] [--run-daemon {0,1}]
                 [--chromium-bin CHROMIUM_BIN] [--daemon-host DAEMON_HOST] [--daemon-p2p-port DAEMON_P2P_PORT] [--daemon-rpc-url DAEMON_RPC_URL] [--wallet-rpc-url WALLET_RPC_URL] [--wallet-rpc-port WALLET_RPC_PORT]
                 [--wallet-rpc-user WALLET_RPC_USER] [--wallet-rpc-password WALLET_RPC_PASSWORD] [--wallet-name WALLET_NAME] [--wallet-password WALLET_PASSWORD]
                 [cmd ...]
```

## Server
Server is based on multiple docker images. We will put more info later.
You can see [openapi schema](config/api.yaml)
