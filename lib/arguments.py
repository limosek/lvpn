import os.path
import platform


class SharedArguments:

    @classmethod
    def define(cls, p, cfgdir, vardir, appdir, env_prefix, mode):
        os.environ[env_prefix + "_CFG_DIR"] = cfgdir
        os.environ[env_prefix + "_VAR_DIR"] = vardir
        os.environ[env_prefix + "_APP_DIR"] = appdir
        p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path')
        p.add_argument('-l', '--log-level', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       env_var=env_prefix + '_LOGLEVEL')
        p.add_argument("--log-file", help="Log file")
        p.add_argument("--audit-file", help="Audit file for storing all payments and transactions")

        if mode == "client":
            p.add_argument("--http-port", help="HTTP port to use for manager", default=8124)
        else:
            p.add_argument("--http-port", help="HTTP port to use for manager", default=8123)

        p.add_argument("--var-dir", help="Var directory", default=os.getenv(env_prefix + "_VAR_DIR"),
                       env_var=env_prefix + "_VAR_DIR")
        p.add_argument("--cfg-dir", help="Cfg directory", default=os.getenv(env_prefix + "_CFG_DIR"),
                       env_var=env_prefix + "_CFG_DIR")
        p.add_argument("--app-dir", help="App directory", default=os.getenv(env_prefix + "_APP_DIR"))
        p.add_argument("--tmp-dir", help="Temp directory", default=os.getenv(env_prefix + "_VAR_DIR") + "/tmp",
                       env_var=env_prefix + "_TMP_DIR")

        p.add_argument('--daemon-host', help='Daemon host', default='localhost')
        p.add_argument('--daemon-bin', help='Daemon binary file', default="letheand")
        p.add_argument('--daemon-rpc-url', help='Daemon RPC URL', default="http://localhost:48782/json_rpc")
        p.add_argument('--daemon-p2p-port', help='Daemon P2P port', type=int, default=48772)
        p.add_argument('--wallet-rpc-bin', help='Wallet RPC binary file', default="lethean-wallet-rpc")
        p.add_argument('--wallet-cli-bin', help='Wallet CLI binary file', default="lethean-wallet-cli")
        p.add_argument('--wallet-rpc-url', help='Wallet RPC URL', default='http://localhost:1444/json_rpc')
        p.add_argument('--wallet-rpc-port', help='Wallet RPC port', type=int, default=1444)
        p.add_argument('--wallet-rpc-user', help='Wallet RPC user', default='vpn')

        if mode == "server":
            p.add_argument('--wallet-rpc-password', help='Wallet RPC password. If not entered, wallet subprocess is not started and payments are not processed.')
            p.add_argument('--db', type=str, default="%s/server.sqlite" % os.getenv(env_prefix + "_VAR_DIR"),
                           help="Database file to use. Default to client.sqlite or server.sqlite")
        else:
            p.add_argument('--wallet-rpc-password', help='Wallet RPC password. Default is to generate random.')
            p.add_argument('--db', type=str, default="%s/client.sqlite" % os.getenv(env_prefix + "_VAR_DIR"),
                           help="Database file to use. Default to client.sqlite or server.sqlite")
        p.add_argument('--wallet-address', help='Wallet public address')

        if mode == "server":
            p.add_argument('--manager-local-bind', help='Bind address to use for manager', default="0.0.0.0")
        else:
            p.add_argument('--manager-local-bind', help='Bind address to use for manager', default="127.0.0.1")
        p.add_argument('--manager-bearer-auth', help='Bearer authentication string for private APIs', default=None)
        p.add_argument('--readonly-providers', default="",
                       help='List of providers, delimited by comma, which cannot be updated by VDP from outside. Default to respect --my-providers')

        p.add_argument("--sessions-dir", help="Directory containing all sessions",
                       default=os.path.abspath(vardir + "/sessions"))

        p.add_argument("--coin-type", help="Coin type to sue", default="lethean", type=str,
                       choices=["lethean"])
        p.add_argument("--coin-unit", help="Coin minimal unit", type=float, default=1e-8)
        p.add_argument("--lthn-price",
                       help="Price for 1 LTHN. Use fixed number for fixed price or use *factor to factor actual price by number")

        p.add_argument('--force-manager-url', help='Manually override manager url for all spaces. Used just for tests')
        p.add_argument('--force-manager-wallet',
                       help='Manually override wallet address url for all spaces. Used just for tests')
        p.add_argument('--on-session-activation',
                       help='External script to be run on session activation. Session file is passed as argument.')
        p.add_argument('--on-session-deactivation',
                       help='External script to be run on session deactivation. Session file is passed as argument.')
        p.add_argument('--default-pay-days', default=30, type=int,
                       help='How many days to pay by default for paid services.')
        p.add_argument('--unpaid-expiry', type=int, default=3600,
                       help='How long time in seconds before unpaid session is deleted')
        p.add_argument('--use-tx-pool', type=bool, default=False,
                       help='Use payments from pool (not confirmed by network) to accept payments.')
        p.add_argument('--wg-map-device', type=str, action='append', default=[],
                       help="Wireguard device map mapping gateid to device name. Use gateid,name")
        p.add_argument('--wg-map-privkey', type=str, action='append', default=[],
                       help="Wireguard private key mapping gateid key. Use gateid,key")
        p.add_argument('--wg-cmd-prefix', type=str, default="",
                       help="Wireguard prefix to run wg command. Can be 'sudo' or 'ssh root@server' or anything else what will be prepended before wg command.")
        if platform.system() == "Windows":
            p.add_argument('--wg-cmd-set-ip', type=str, default="netsh interface {af} set address {iface} {type} {ip}/{prefix}",
                           help="Wireguard command to assign IP address to interface")
            p.add_argument('--wg-cmd-unset-ips', type=str,
                           default="",
                           help="Wireguard command to unset IP addresses from interface")
            p.add_argument('--wg-cmd-set-interface-up', type=str, default=None,
                           help="Wireguard command to set interface up")
            p.add_argument('--wg-cmd-create-interface', type=str, default='"C:\\Program Files\\WireGuard\\wireguard.exe" /installtunnelservice "{fname}"',
                           help="Wireguard command to create interface. Default to not manage interfaces")
            p.add_argument('--wg-cmd-delete-interface', type=str, default='"C:\\Program Files\\WireGuard\\wireguard.exe" /uninstalltunnelservice "{iface}"',
                           help="Wireguard command to delete interface. Default to not manage interfaces")
            p.add_argument('--wg-cmd-route', type=str, default="route add {network} MASK {mask} {gw}",
                           help="Wireguard command to route network.")
            p.add_argument('--wg-cmd-nat', type=str,
                           default="",
                           help="Wireguard command to masquerade route")
        else:
            p.add_argument('--wg-cmd-set-ip', type=str, default="ip addr add dev {iface} {ip}/{prefix}",
                       help="Wireguard command to assign IP address to interface")
            p.add_argument('--wg-cmd-unset-ips', type=str,
                           default="ip addr flush dev {iface}",
                           help="Wireguard command to unset IP addresses from interface")

            p.add_argument('--wg-cmd-set-interface-up', type=str, default="ip link set up dev {iface}",
                           help="Wireguard command to set interface up")
            p.add_argument('--wg-cmd-create-interface', type=str, default="ip link add dev {iface} type wireguard",
                       help="Wireguard command to create interface.")
            p.add_argument('--wg-cmd-delete-interface', type=str, default="ip link del dev {iface}",
                       help="Wireguard command to delete interface.")
            p.add_argument('--wg-cmd-route', type=str, default="ip route add {network} via {gw}",
                           help="Wireguard command to route network.")
            p.add_argument('--wg-cmd-nat', type=str, default="",
                           help="Wireguard command to masquerade route")

        p.add_argument("--enable-wg", type=int, choices=[0, 1], help="Enable wireguard support", default=0)

        p.add_argument("--provider-id", help="Providerid used as local provider to serve. Defaults to read from provider-public-key",
                       default="")
        p.add_argument('--is-client', type=bool, help='For internal usage', default=False)
        p.add_argument('--is-server', type=bool, help='For internal usage', default=False)
        p.add_argument('--single-thread', type=int, choices=[0, 1], help='For internal usage', default=0)

        return p
