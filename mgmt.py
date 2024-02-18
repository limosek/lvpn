import json
import configargparse
import logging
import nacl.signing
import nacl.encoding
import os
import sys
import ownca

os.environ["NO_KIVY"] = "1"

from client.sshproxy import SSHProxy
from lib.mngrrpc import ManagerRpcCall
from lib.session import Session
from lib.sessions import Sessions
from lib.signverify import Sign, Verify
from lib.vdp import VDP
from lib.wizard import Wizard


def main():
    if not os.getenv("WLS_CFG_DIR"):
        os.environ["WLS_CFG_DIR"] = "/etc/lvpn"
    if not os.getenv("WLS_VAR_DIR"):
        os.environ["WLS_VAR_DIR"] = os.path.expanduser("~") + "/lvpn"

    p = configargparse.ArgParser(default_config_files=['/etc/lthn/mgmt.conf'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path', env_var='WLS_CONFIG')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING',
                   env_var='WLS_LOGLEVEL')
    p.add_argument("--ca-dir", help="Directory for Certificate authority",
                   default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ca"))
    p.add_argument("--app-dir", help="App directory", default=os.path.dirname(__file__))
    p.add_argument("--var-dir", help="Var directory", default=os.getenv("WLS_VAR_DIR"), env_var="WLS_VAR_DIR")
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs",
                   default=os.getenv("WLS_VAR_DIR") + "/spaces")
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs",
                   default=os.getenv("WLS_VAR_DIR") + "/gates")
    p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                   default=os.getenv("WLS_VAR_DIR") + "/providers")
    p.add_argument("--provider-private-key", help="Provider private key file",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.private")
    p.add_argument("--provider-public-key", help="Provider public key file",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.public")
    p.add_argument("--sessions-dir", help="Directory containing all sessions",
                   default=os.getenv("WLS_VAR_DIR") + "/sessions")
    p.add_argument('--force-manager-url', help='Manually override manager url for all spaces. Used just for tests')
    p.add_argument("cmd", help="Command to be used", type=str, choices={
        "init": "Initialize files",
        "show-vdp": "Print VDP from actual spaces and gates to stdout",
        "generate-provider-keys": "Generate provider public and private keys",
        "generate-cfg": "Generate config file",
        "sign-text": "Sign text by provider",
        "verify-text": "Verify text signed by provider",
        "issue-crt": "Issue certificate",
        "generate-ca": "Generate certificate authority",
        "generate-vdp": "Generate basic VDP data for provider",
        "create-session": "Create session to connect to gate/space",
        "prepare-session-data": "Prepare local files for session"
    })
    p.add_argument("args", help="Args for command", nargs="*")

    cfg = p.parse_args()
    cfg.readonly_providers = []
    logging.basicConfig(level=cfg.l)

    if cfg.cmd == "show-vdp":
        vdp = VDP(cfg)
        print(vdp.get_json())

    elif cfg.cmd == "init":
        Wizard.files(cfg)

    elif cfg.cmd == "generate-provider-keys":

        # Step 1: Key generation
        signing_key = nacl.signing.SigningKey.generate()
        verification_key = signing_key.verify_key

        # Step 2: Convert keys to bytes for storage
        signing_key_bytes = signing_key.encode(encoder=nacl.encoding.HexEncoder)
        verification_key_bytes = verification_key.encode(encoder=nacl.encoding.HexEncoder)
        with open(cfg.provider_private_key, 'wb') as private_key_file:
            private_key_file.write(signing_key_bytes)
        with open(cfg.provider_public_key, 'wb') as public_key_file:
            public_key_file.write(verification_key_bytes)
        print(f"Private Key (NEVER SHARE THIS!): {signing_key_bytes.decode()}")
        print(f"Public Key: {verification_key_bytes.decode()}")

    elif cfg.cmd == "sign-text":
        if cfg.args:
            msg = cfg.args[0]
            signed = Sign(cfg.provider_private_key).sign(msg)
            print(signed)

        else:
            logging.error("Need sign-text 'text'")
            sys.exit(1)

    elif cfg.cmd == "verify-text":
        if cfg.args and (2 <= len(cfg.args) <= 3):
            msg = cfg.args[0]
            signed = cfg.args[1]
            if len(cfg.args) == 3:
                providerid = cfg.args[2]
            else:
                providerid = cfg.provider_public_key
            result = Verify(providerid).verify(msg, signed)
            if result:
                print("OK")
                sys.exit()
            else:
                print("Signature Not valid.")
                sys.exit(1)
        else:
            logging.error("Need verify-text 'text' 'signed' [providerid]")
            sys.exit(1)

    elif cfg.cmd == "generate-cfg":
        Wizard.cfg(cfg, os.environ["WLS_CFG_DIR"])

    elif cfg.cmd == "generate-ca":
        if cfg.args and len(cfg.args) == 2:
            ownca.CertificateAuthority(ca_storage=cfg.ca_dir, common_name=cfg.args[0], maximum_days=int(cfg.args[1]))
            print("Generated new CA to directory %s" % cfg.ca_dir)
        else:
            logging.error("Need generate-ca 'common_name' 'days'")
            sys.exit(1)

    elif cfg.cmd == "issue-crt":
        if cfg.args and len(cfg.args) == 2:
            ca = ownca.CertificateAuthority(ca_storage=cfg.ca_dir)
            ca.issue_certificate(cfg.args[0], common_name=cfg.args[0], maximum_days=int(cfg.args[1]), key_size=4096)
            print(ca.key_bytes.decode("utf-8"))
            print(ca.cert_bytes.decode("utf-8"))
        else:
            logging.error("Need issue-certificate hostname days")
            sys.exit(1)

    elif cfg.cmd == "generate-vdp":
        if cfg.args and len(cfg.args) == 4:
            name = cfg.args[0]
            space = cfg.args[1]
            fqdn = cfg.args[2]
            wallet = cfg.args[3]
            Wizard.provider_vdp(cfg, name,  space, wallet, fqdn)
        else:
            logging.error("Need generate-vdp 'name' 'space' 'fqdn' 'wallet'")
            sys.exit(1)

    elif cfg.cmd == "create-session":
        if cfg.args and len(cfg.args) == 3:
            gateid = cfg.args[0]
            spaceid = cfg.args[1]
            cfg.vdp = VDP(cfg)
            days = cfg.args[2]
            gate = cfg.vdp.get_gate(gateid)
            space = cfg.vdp.get_space(spaceid)
            if gate and space:
                url = space.get_manager_url()
                mngr = ManagerRpcCall(url)
                s = mngr.create_session(gateid, spaceid, int(days))
                session = Session(cfg, s)
                print(json.dumps(session.get_dict(), indent=2))
                if session.get_gate_data("ssh"):
                    print(session.get_gate_data("ssh")["key"])
                    print(session.get_gate_data("ssh")["crt"])
            else:
                logging.error("Unknown gate or space")
                sys.exit(1)

    elif cfg.cmd == "prepare-session-data":
        if cfg.args and len(cfg.args) == 2:
            sessionid = cfg.args[0]
            dir = cfg.args[1]
            if not os.path.exists(dir):
                os.mkdir(dir)
            cfg.vdp = VDP(cfg)
            sessions = Sessions(cfg)
            session = sessions.get(sessionid)
            if session:
                if session.get_gate_data("ssh"):
                    print(json.dumps(SSHProxy.prepare(session, dir, []), indent=2))
            else:
                logging.errod("Bad sessionid")
                sys.exit(2)
        else:
            logging.error("Use prepare-session-data sessionid directory")
            sys.exit(1)

    else:
        print("Bad command!")
        p.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
