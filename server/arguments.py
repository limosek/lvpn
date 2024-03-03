import os


class ServerArguments:

    @classmethod
    def define(cls, p, cfgdir, vardir, appdir):
        p.add_argument("--stripe-api-key", help="Stripe private key for payments")
        p.add_argument("--stripe-plink-id", help="Stripe payment link id for payment")
        p.add_argument("--tradeogre-api-key", help="TradeOgre API key for conversions")
        p.add_argument("--tradeogre-api-secret", help="TradeOgre API secret key for conversions")
        p.add_argument("--provider-private-key", help="Private provider key",
                       default=cfgdir + "/provider.private")
        p.add_argument("--provider-public-key", help="Public provider key",
                       default=cfgdir + "/provider.public")
        p.add_argument("--ca-dir", help="Directory for Certificate authority",
                       default=cfgdir + "/ca")
        p.add_argument("--ca-name", help="Common name for CA creation",
                       default="LVPN-easy-provider")
        p.add_argument("--ssh-user-ca-private", help="SSH User CA private file",
                       default=cfgdir + "/ssh-user-ca")
        p.add_argument("--ssh-user-ca-public", help="SSH User CA public file",
                       default=cfgdir + "/ssh-user-ca.pub")
        p.add_argument("--ssh-host-ca-private", help="SSH Host CA private file",
                       default=cfgdir + "/ssh-host-ca")
        p.add_argument("--ssh-host-ca-public", help="SSH Host CA public file",
                       default=cfgdir + "/ssh-host-ca.pub")
        p.add_argument("--ssh-user-key", help="SSH User key",
                       default=cfgdir + "/ssh-user")
        p.add_argument("--ignore-wg-key-mismatch", type=int, help="Ignore bad public/private keys. Mostly for testing",
                       default=0, choices=[0, 1])
        p.add_argument("--max-free-session-days", type=int, help="Maximum length of free session in days",
                       default=1)
        p.add_argument("--max-free-wg-handshake-timeout", type=int, help="Maximum handshake timeout. Free WG sessions will be deleted after this seconds.",
                       default=3600)

        return p
