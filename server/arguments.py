import os


class ServerArguments:

    @classmethod
    def define(cls, p, cfgdir, vardir, appdir):
        p.add_argument("--stripe-api-key", help="Stripe private key for payments")
        p.add_argument("--stripe-plink-id", help="Stripe payment link id for payment")
        p.add_argument("--tradeogre-api-key", help="TradeOgre API key for conversions")
        p.add_argument("--tradeogre-api-secret", help="TradeOgre API secret key for conversions")
        p.add_argument("--provider-private-key", help="Private provider key",
                       default=os.getenv("WLS_CFG_DIR") + "/provider.private")
        p.add_argument("--provider-public-key", help="Public provider key",
                       default=os.getenv("WLS_CFG_DIR") + "/provider.public")
        p.add_argument("--ca-dir", help="Directory for Certificate authority",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ca"))
        p.add_argument("--ca-name", help="Common name for CA creation",
                       default="LVPN-easy-provider")
        p.add_argument("--ssh-user-ca-private", help="SSH User CA private file",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ssh-user-ca"))
        p.add_argument("--ssh-user-ca-public", help="SSH User CA public file",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ssh-user-ca.pub"))
        p.add_argument("--ssh-host-ca-private", help="SSH Host CA private file",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ssh-host-ca"))
        p.add_argument("--ssh-host-ca-public", help="SSH Host CA public file",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ssh-host-ca.pub"))
        p.add_argument("--ssh-user-key", help="SSH User key",
                       default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ssh-user"))

        return p
