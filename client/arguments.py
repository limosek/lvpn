

class ClientArguments:

    @classmethod
    def define(cls, p, cfgdir, vardir, appdir):

        p.add_argument('--run-gui', default=1, type=int, choices=[0, 1], help='Run GUI')
        p.add_argument('--run-proxy', default=1, type=int, choices=[0, 1], help='Run local proxy')
        p.add_argument('--run-wallet', default=1, type=int, choices=[0, 1], help='Run local wallet')
        p.add_argument('--run-daemon', default=0, type=int, choices=[0, 1], help='Run local daemon RPC')
        p.add_argument('--wallet-name', help='Wallet name', default="wallet-lthn")
        p.add_argument('--wallet-password', help='Wallet password')

        p.add_argument('--edge-bin', help='Edge browser binary',
                       default="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        p.add_argument('--chromium-bin', help='Chromium browser binary', default="chromium")

        p.add_argument('--use-http-proxy', type=str, help='Use HTTP proxy (CONNECT) to services', env_var="HTTP_PROXY")

        p.add_argument('--local-bind', help='Bind address to use for proxy and TLS ports', default="127.0.0.1")

        p.add_argument('--max-tls-connections', help='How many connection at maximum to back-off', type=int, default=20)

        p.add_argument('--ssh-engine', help='SSH engine to use', choices=["paramiko", "ssh"], default="ssh")

        p.add_argument('--auto-connect', type=str, help='Auto connect uris',
                       default="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free,paid"
                       )
        p.add_argument('--auto-reconnect', type=bool, help='Auto reconnect on failure', default=False)
        p.add_argument('--auto-pay-days', type=int, default=0,
                       help='Auto pay service when there is an request to connect for this number of days. By default, payment must be confirmed by GUI')
        p.add_argument('--free-session-days', type=int,
                       help='How many days to request for free service', default=1)

        try:
            p.add_argument('--contributions', type=str,
                       help='Contribute other parties by using this service as a client (increase price).',
                       default="")
        except Exception as e:
            """We probably already defined within server args"""
            pass

        return p

