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
You can see [openapi schema](misc/schemas/client.yaml)

```commandline
usage: client.py [-h] [-c CONFIG] [-l {DEBUG,INFO,WARNING,ERROR}] [--log-file LOG_FILE] [--http-port HTTP_PORT] [--var-dir VAR_DIR] [--cfg-dir CFG_DIR] [--app-dir APP_DIR]
                 [--tmp-dir TMP_DIR] [--daemon-host DAEMON_HOST] [--daemon-bin DAEMON_BIN] [--daemon-rpc-url DAEMON_RPC_URL] [--daemon-p2p-port DAEMON_P2P_PORT]
                 [--wallet-rpc-bin WALLET_RPC_BIN] [--wallet-cli-bin WALLET_CLI_BIN] [--wallet-rpc-url WALLET_RPC_URL] [--wallet-rpc-port WALLET_RPC_PORT]
                 [--wallet-rpc-user WALLET_RPC_USER] [--wallet-rpc-password WALLET_RPC_PASSWORD] [--wallet-address WALLET_ADDRESS] [--spaces-dir SPACES_DIR] [--gates-dir GATES_DIR]
                 [--providers-dir PROVIDERS_DIR] [--my-spaces-dir MY_SPACES_DIR] [--my-gates-dir MY_GATES_DIR] [--my-providers-dir MY_PROVIDERS_DIR]
                 [--manager-local-bind MANAGER_LOCAL_BIND] [--manager-bearer-auth MANAGER_BEARER_AUTH] [--readonly-providers READONLY_PROVIDERS] [--sessions-dir SESSIONS_DIR]
                 [--coin-type {lethean}] [--coin-unit COIN_UNIT] [--lthn-price LTHN_PRICE] [--force-manager-url FORCE_MANAGER_URL] [--force-manager-wallet FORCE_MANAGER_WALLET]
                 [--on-session-activation ON_SESSION_ACTIVATION] [--unpaid-expiry UNPAID_EXPIRY] [--use-tx-pool USE_TX_POOL] [--run-gui {0,1}] [--run-proxy {0,1}] [--run-wallet {0,1}]
                 [--run-daemon {0,1}] [--wallet-name WALLET_NAME] [--wallet-password WALLET_PASSWORD] [--edge-bin EDGE_BIN] [--chromium-bin CHROMIUM_BIN]
                 [--use-http-proxy USE_HTTP_PROXY] [--local-bind LOCAL_BIND] [--ssh-engine {paramiko,ssh}] [--auto-connect AUTO_CONNECT]

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Config file path
  -l {DEBUG,INFO,WARNING,ERROR}, --log-level {DEBUG,INFO,WARNING,ERROR}
                        Log level [env var: WLC_LOGLEVEL]
  --log-file LOG_FILE   Log file
  --http-port HTTP_PORT
                        HTTP port to use for manager
  --var-dir VAR_DIR     Var directory [env var: WLC_VAR_DIR]
  --cfg-dir CFG_DIR     Cfg directory [env var: WLC_CFG_DIR]
  --app-dir APP_DIR     App directory
  --tmp-dir TMP_DIR     Temp directory [env var: WLC_TMP_DIR]
  --daemon-host DAEMON_HOST
                        Daemon host
  --daemon-bin DAEMON_BIN
                        Daemon binary file
  --daemon-rpc-url DAEMON_RPC_URL
                        Daemon RPC URL
  --daemon-p2p-port DAEMON_P2P_PORT
                        Daemon P2P port
  --wallet-rpc-bin WALLET_RPC_BIN
                        Wallet RPC binary file
  --wallet-cli-bin WALLET_CLI_BIN
                        Wallet CLI binary file
  --wallet-rpc-url WALLET_RPC_URL
                        Wallet RPC URL
  --wallet-rpc-port WALLET_RPC_PORT
                        Wallet RPC port
  --wallet-rpc-user WALLET_RPC_USER
                        Wallet RPC user
  --wallet-rpc-password WALLET_RPC_PASSWORD
                        Wallet RPC password. Default is to generate random.
  --wallet-address WALLET_ADDRESS
                        Wallet public address
  --spaces-dir SPACES_DIR
                        Directory containing all spaces VDPs
  --gates-dir GATES_DIR
                        Directory containing all gateway VDPs
  --providers-dir PROVIDERS_DIR
                        Directory containing all provider VDPs
  --my-spaces-dir MY_SPACES_DIR
                        Directory containing our VDPs
  --my-gates-dir MY_GATES_DIR
                        Directory containing our gateway VDPs
  --my-providers-dir MY_PROVIDERS_DIR
                        Directory containing our provider VDPs
  --manager-local-bind MANAGER_LOCAL_BIND
                        Bind address to use for manager
  --manager-bearer-auth MANAGER_BEARER_AUTH
                        Bearer authentication string for private APIs
  --readonly-providers READONLY_PROVIDERS
                        List of providers, delimited by comma, which cannot be updated by VDP from outside.
  --sessions-dir SESSIONS_DIR
                        Directory containing all sessions
  --coin-type {lethean}
                        Coin type to sue
  --coin-unit COIN_UNIT
                        Coin minimal unit
  --lthn-price LTHN_PRICE
                        Price for 1 LTHN. Use fixed number for fixed price or use *factor to factor actual price by number
  --force-manager-url FORCE_MANAGER_URL
                        Manually override manager url for all spaces. Used just for tests
  --force-manager-wallet FORCE_MANAGER_WALLET
                        Manually override wallet address url for all spaces. Used just for tests
  --on-session-activation ON_SESSION_ACTIVATION
                        External script to be run on session activation. Session file is passed as argument.
  --unpaid-expiry UNPAID_EXPIRY
                        How long time in seconds before unpaid session is deleted
  --use-tx-pool USE_TX_POOL
                        Use payments from pool (not confirmed by network) to accept payments.
  --run-gui {0,1}       Run GUI
  --run-proxy {0,1}     Run local proxy
  --run-wallet {0,1}    Run local wallet
  --run-daemon {0,1}    Run local daemon RPC
  --wallet-name WALLET_NAME
                        Wallet name
  --wallet-password WALLET_PASSWORD
                        Wallet password
  --edge-bin EDGE_BIN   Edge browser binary
  --chromium-bin CHROMIUM_BIN
                        Chromium browser binary
  --use-http-proxy USE_HTTP_PROXY
                        Use HTTP proxy (CONNECT) to services [env var: HTTP_PROXY]
  --local-bind LOCAL_BIND
                        Bind address to use for proxy and TLS ports
  --ssh-engine {paramiko,ssh}
                        SSH engine to use
  --auto-connect AUTO_CONNECT
                        Auto connect uris

Args that start with '--' can also be set in a config file (/etc/lvpn/client.ini or /etc/lvpn//client.ini or /home/lm-a/lvpn//client.ini or specified via -c). Config file syntax allows:
key=value, flag=true, stuff=[a,b,c] (for details, see syntax at https://goo.gl/R74nmi). In general, command-line values override environment variables which override config file values
which override defaults.
```

## Server
Server is based on multiple docker images. We will put more info later.
You can see [openapi schema](misc/schemas/server.yaml)
```commandline
usage: server.py [-h] [-c CONFIG] [-l {DEBUG,INFO,WARNING,ERROR}] [--log-file LOG_FILE] [--http-port HTTP_PORT] [--var-dir VAR_DIR] [--cfg-dir CFG_DIR] [--app-dir APP_DIR]
                 [--tmp-dir TMP_DIR] [--daemon-host DAEMON_HOST] [--daemon-bin DAEMON_BIN] [--daemon-rpc-url DAEMON_RPC_URL] [--daemon-p2p-port DAEMON_P2P_PORT]
                 [--wallet-rpc-bin WALLET_RPC_BIN] [--wallet-cli-bin WALLET_CLI_BIN] [--wallet-rpc-url WALLET_RPC_URL] [--wallet-rpc-port WALLET_RPC_PORT]
                 [--wallet-rpc-user WALLET_RPC_USER] --wallet-rpc-password WALLET_RPC_PASSWORD [--wallet-address WALLET_ADDRESS] [--spaces-dir SPACES_DIR] [--gates-dir GATES_DIR]
                 [--providers-dir PROVIDERS_DIR] [--my-spaces-dir MY_SPACES_DIR] [--my-gates-dir MY_GATES_DIR] [--my-providers-dir MY_PROVIDERS_DIR]
                 [--manager-local-bind MANAGER_LOCAL_BIND] [--manager-bearer-auth MANAGER_BEARER_AUTH] [--readonly-providers READONLY_PROVIDERS] [--sessions-dir SESSIONS_DIR]
                 [--coin-type {lethean}] [--coin-unit COIN_UNIT] [--lthn-price LTHN_PRICE] [--force-manager-url FORCE_MANAGER_URL] [--force-manager-wallet FORCE_MANAGER_WALLET]
                 [--on-session-activation ON_SESSION_ACTIVATION] [--unpaid-expiry UNPAID_EXPIRY] [--use-tx-pool USE_TX_POOL] [--stripe-api-key STRIPE_API_KEY]
                 [--stripe-plink-id STRIPE_PLINK_ID] [--tradeogre-api-key TRADEOGRE_API_KEY] [--tradeogre-api-secret TRADEOGRE_API_SECRET] [--provider-private-key PROVIDER_PRIVATE_KEY]
                 [--provider-public-key PROVIDER_PUBLIC_KEY] [--ca-dir CA_DIR] [--ca-name CA_NAME] [--ssh-user-ca-private SSH_USER_CA_PRIVATE] [--ssh-user-ca-public SSH_USER_CA_PUBLIC]
                 [--ssh-host-ca-private SSH_HOST_CA_PRIVATE] [--ssh-host-ca-public SSH_HOST_CA_PUBLIC] [--ssh-user-key SSH_USER_KEY]

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Config file path
  -l {DEBUG,INFO,WARNING,ERROR}, --log-level {DEBUG,INFO,WARNING,ERROR}
                        Log level [env var: WLS_LOGLEVEL]
  --log-file LOG_FILE   Log file
  --http-port HTTP_PORT
                        HTTP port to use for manager
  --var-dir VAR_DIR     Var directory [env var: WLS_VAR_DIR]
  --cfg-dir CFG_DIR     Cfg directory [env var: WLS_CFG_DIR]
  --app-dir APP_DIR     App directory
  --tmp-dir TMP_DIR     Temp directory [env var: WLS_TMP_DIR]
  --daemon-host DAEMON_HOST
                        Daemon host
  --daemon-bin DAEMON_BIN
                        Daemon binary file
  --daemon-rpc-url DAEMON_RPC_URL
                        Daemon RPC URL
  --daemon-p2p-port DAEMON_P2P_PORT
                        Daemon P2P port
  --wallet-rpc-bin WALLET_RPC_BIN
                        Wallet RPC binary file
  --wallet-cli-bin WALLET_CLI_BIN
                        Wallet CLI binary file
  --wallet-rpc-url WALLET_RPC_URL
                        Wallet RPC URL
  --wallet-rpc-port WALLET_RPC_PORT
                        Wallet RPC port
  --wallet-rpc-user WALLET_RPC_USER
                        Wallet RPC user
  --wallet-rpc-password WALLET_RPC_PASSWORD
                        Wallet RPC password.
  --wallet-address WALLET_ADDRESS
                        Wallet public address
  --spaces-dir SPACES_DIR
                        Directory containing all spaces VDPs
  --gates-dir GATES_DIR
                        Directory containing all gateway VDPs
  --providers-dir PROVIDERS_DIR
                        Directory containing all provider VDPs
  --my-spaces-dir MY_SPACES_DIR
                        Directory containing our VDPs
  --my-gates-dir MY_GATES_DIR
                        Directory containing our gateway VDPs
  --my-providers-dir MY_PROVIDERS_DIR
                        Directory containing our provider VDPs
  --manager-local-bind MANAGER_LOCAL_BIND
                        Bind address to use for manager
  --manager-bearer-auth MANAGER_BEARER_AUTH
                        Bearer authentication string for private APIs
  --readonly-providers READONLY_PROVIDERS
                        List of providers, delimited by comma, which cannot be updated by VDP from outside.
  --sessions-dir SESSIONS_DIR
                        Directory containing all sessions
  --coin-type {lethean}
                        Coin type to sue
  --coin-unit COIN_UNIT
                        Coin minimal unit
  --lthn-price LTHN_PRICE
                        Price for 1 LTHN. Use fixed number for fixed price or use *factor to factor actual price by number
  --force-manager-url FORCE_MANAGER_URL
                        Manually override manager url for all spaces. Used just for tests
  --force-manager-wallet FORCE_MANAGER_WALLET
                        Manually override wallet address url for all spaces. Used just for tests
  --on-session-activation ON_SESSION_ACTIVATION
                        External script to be run on session activation. Session file is passed as argument.
  --unpaid-expiry UNPAID_EXPIRY
                        How long time in seconds before unpaid session is deleted
  --use-tx-pool USE_TX_POOL
                        Use payments from pool (not confirmed by network) to accept payments.
  --stripe-api-key STRIPE_API_KEY
                        Stripe private key for payments
  --stripe-plink-id STRIPE_PLINK_ID
                        Stripe payment link id for payment
  --tradeogre-api-key TRADEOGRE_API_KEY
                        TradeOgre API key for conversions
  --tradeogre-api-secret TRADEOGRE_API_SECRET
                        TradeOgre API secret key for conversions
  --provider-private-key PROVIDER_PRIVATE_KEY
                        Private provider key
  --provider-public-key PROVIDER_PUBLIC_KEY
                        Public provider key
  --ca-dir CA_DIR       Directory for Certificate authority
  --ca-name CA_NAME     Common name for CA creation
  --ssh-user-ca-private SSH_USER_CA_PRIVATE
                        SSH User CA private file
  --ssh-user-ca-public SSH_USER_CA_PUBLIC
                        SSH User CA public file
  --ssh-host-ca-private SSH_HOST_CA_PRIVATE
                        SSH Host CA private file
  --ssh-host-ca-public SSH_HOST_CA_PUBLIC
                        SSH Host CA public file
  --ssh-user-key SSH_USER_KEY
                        SSH User key

Args that start with '--' can also be set in a config file (/etc/lvpn/server.ini or specified via -c). Config file syntax allows: key=value, flag=true, stuff=[a,b,c] (for details, see
syntax at https://goo.gl/R74nmi). In general, command-line values override environment variables which override config file values which override defaults.
```

## Mgmt
This is management utility used for server and client.
```commandline
usage: mgmt.py [-h] [-c CONFIG] [-l {DEBUG,INFO,WARNING,ERROR}] [--log-file LOG_FILE] [--http-port HTTP_PORT] [--var-dir VAR_DIR] [--cfg-dir CFG_DIR] [--app-dir APP_DIR]
               [--tmp-dir TMP_DIR] [--daemon-host DAEMON_HOST] [--daemon-bin DAEMON_BIN] [--daemon-rpc-url DAEMON_RPC_URL] [--daemon-p2p-port DAEMON_P2P_PORT]
               [--wallet-rpc-bin WALLET_RPC_BIN] [--wallet-cli-bin WALLET_CLI_BIN] [--wallet-rpc-url WALLET_RPC_URL] [--wallet-rpc-port WALLET_RPC_PORT]
               [--wallet-rpc-user WALLET_RPC_USER] [--wallet-rpc-password WALLET_RPC_PASSWORD] [--wallet-address WALLET_ADDRESS] [--spaces-dir SPACES_DIR] [--gates-dir GATES_DIR]
               [--providers-dir PROVIDERS_DIR] [--my-spaces-dir MY_SPACES_DIR] [--my-gates-dir MY_GATES_DIR] [--my-providers-dir MY_PROVIDERS_DIR]
               [--manager-local-bind MANAGER_LOCAL_BIND] [--manager-bearer-auth MANAGER_BEARER_AUTH] [--readonly-providers READONLY_PROVIDERS] [--sessions-dir SESSIONS_DIR]
               [--coin-type {lethean}] [--coin-unit COIN_UNIT] [--lthn-price LTHN_PRICE] [--force-manager-url FORCE_MANAGER_URL] [--force-manager-wallet FORCE_MANAGER_WALLET]
               [--on-session-activation ON_SESSION_ACTIVATION] [--unpaid-expiry UNPAID_EXPIRY] [--use-tx-pool USE_TX_POOL] [--stripe-api-key STRIPE_API_KEY]
               [--stripe-plink-id STRIPE_PLINK_ID] [--tradeogre-api-key TRADEOGRE_API_KEY] [--tradeogre-api-secret TRADEOGRE_API_SECRET] [--provider-private-key PROVIDER_PRIVATE_KEY]
               [--provider-public-key PROVIDER_PUBLIC_KEY] [--ca-dir CA_DIR] [--ca-name CA_NAME] [--ssh-user-ca-private SSH_USER_CA_PRIVATE] [--ssh-user-ca-public SSH_USER_CA_PUBLIC]
               [--ssh-host-ca-private SSH_HOST_CA_PRIVATE] [--ssh-host-ca-public SSH_HOST_CA_PUBLIC] [--ssh-user-key SSH_USER_KEY] [--run-gui {0,1}] [--run-proxy {0,1}]
               [--run-wallet {0,1}] [--run-daemon {0,1}] [--wallet-name WALLET_NAME] [--wallet-password WALLET_PASSWORD] [--edge-bin EDGE_BIN] [--chromium-bin CHROMIUM_BIN]
               [--use-http-proxy USE_HTTP_PROXY] [--local-bind LOCAL_BIND] [--ssh-engine {paramiko,ssh}] [--auto-connect AUTO_CONNECT]
               {init,show-vdp,generate-provider-keys,generate-cfg,sign-text,verify-text,issue-crt,generate-ca,generate-vdp,create-session,prepare-client-session} [args ...]

positional arguments:
  {init,show-vdp,generate-provider-keys,generate-cfg,sign-text,verify-text,issue-crt,generate-ca,generate-vdp,create-session,prepare-client-session}
                        Command to be used
  args                  Args for command
```