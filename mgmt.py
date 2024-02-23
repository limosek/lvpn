import json
import configargparse
import logging
import nacl.signing
import nacl.encoding
import os
import sys
import ownca

from lib.registry import Registry

os.environ["NO_KIVY"] = "1"

from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from server.arguments import ServerArguments
from client.tlsproxy import TLSProxy
from client.sshproxy import SSHProxy
from lib.mngrrpc import ManagerRpcCall, ManagerException
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

    p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/mgmt.ini'])
    p = SharedArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__),
                               "WLS", "client")
    p = ServerArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__))
    p = ClientArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__))
    p.add_argument("cmd", help="Command to be used", type=str, choices={
        "init": "Initialize files",
        "show-vdp": "Print VDP from actual spaces and gates to stdout",
        "push-vdp": "Push VDP to server",
        "fetch-vdp": "Fetch VDP and save locally",
        "list-providers": "List actual known providers",
        "list-spaces": "List actual known spaces",
        "list-gates": "List actual known gates",
        "generate-provider-keys": "Generate provider public and private keys",
        "generate-cfg": "Generate config file",
        "sign-text": "Sign text by provider",
        "verify-text": "Verify text signed by provider",
        "issue-crt": "Issue certificate",
        "generate-ca": "Generate certificate authority",
        "generate-vdp": "Generate basic VDP data for provider",
        "create-session": "Create session to connect to gate/space",
        "prepare-client-session": "Prepare client files based on sessionid"
    })
    p.add_argument("args", help="Args for command", nargs="*")

    cfg = p.parse_args()
    cfg.readonly_providers = []
    cfg.l = cfg.log_level
    logging.basicConfig(level=cfg.l)
    Registry.cfg = cfg
    #Registry.vdp = VDP()

    if cfg.cmd == "show-vdp":
        vdp = VDP()
        print(vdp.get_json())

    elif cfg.cmd == "fetch-vdp":
        if cfg.args and len(cfg.args) == 1:
            vdp = VDP()
            if cfg.args[0].startswith("http"):
                url = cfg.args[0]
            else:
                if not vdp.get_provider(cfg.args[0]):
                    print("Unknown providerid!")
                    sys.exit(4)
                url = vdp.get_provider(cfg.args[0]).get_manager_url()
            mgr = ManagerRpcCall(url)
            try:
                jsn = mgr.fetch_vdp()
                vdp = VDP(vdpdata=jsn)
                print(vdp.save())
            except Exception as m:
                print("Error fetching VDP!")
                print(m)
                sys.exit(4)
        else:
            print("Use fetch-vdp providerid-or-url")
            sys.exit(1)

    elif cfg.cmd == "push-vdp":
        if cfg.args and len(cfg.args) == 1:
            vdp = VDP()
            if vdp.get_provider(cfg.args[0]):
                mgr = ManagerRpcCall(vdp.get_provider(cfg.args[0]).get_manager_url())
                try:
                    pushed = mgr.push_vdp(vdp)
                    print(pushed)
                except ManagerException as m:
                    print("Error pushing VDP!")
                    print(m)
                    sys.exit(4)
            else:
                print("Unknown providerid!")
                sys.exit(4)
        else:
            print("Use push-vdp providerid")
            sys.exit(1)

    elif cfg.cmd == "list-providers":
        vdp = VDP()
        print("id,name,local")
        for p in vdp.providers():
            print("%s,%s,%s" % (p.get_id(), p.get_name(), p.is_local()))

    elif cfg.cmd == "list-spaces":
        vdp = VDP()
        print("id,name,local")
        for p in vdp.spaces():
            print("%s,%s,%s" % (p.get_id(), p.get_name(), p.is_local()))

    elif cfg.cmd == "list-gates":
        vdp = VDP()
        print("id,name,local")
        for p in vdp.gates():
            print("%s,%s,%s" % (p.get_id(), p.get_name(), p.is_local()))

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
            cfg.providers_dir = cfg.my_providers_dir
            cfg.spaces_dir = cfg.my_spaces_dir
            cfg.gates_dir = cfg.my_gates_dir
            Wizard.provider_vdp(cfg, name,  space, wallet, fqdn)
        else:
            logging.error("Need generate-vdp 'name' 'space' 'fqdn' 'wallet'")
            sys.exit(1)

    elif cfg.cmd == "create-session":
        if cfg.args and len(cfg.args) == 3:
            gateid = cfg.args[0]
            spaceid = cfg.args[1]
            cfg.vdp = VDP()
            days = cfg.args[2]
            gate = cfg.vdp.get_gate(gateid)
            space = cfg.vdp.get_space(spaceid)
            if gate and space:
                url = space.get_manager_url()
                mngr = ManagerRpcCall(url)
                s = mngr.create_session(gate, space, int(days))
                session = Session(s)
                print(json.dumps(session.get_dict(), indent=2))
                if session.get_gate_data("ssh"):
                    print(session.get_gate_data("ssh")["key"])
                    print(session.get_gate_data("ssh")["crt"])
            else:
                logging.error("Unknown gate or space")
                sys.exit(1)

    elif cfg.cmd == "prepare-client-session":
        if cfg.args and len(cfg.args) == 2:
            sessionid = cfg.args[0]
            dir = cfg.args[1]
            if not os.path.exists(dir):
                os.mkdir(dir)
            cfg.vdp = VDP()
            sessions = Sessions()
            session = sessions.get(sessionid)
            if session:
                if session.get_gate_data("ssh"):
                    print(json.dumps(SSHProxy.prepare(session, dir, []), indent=2))
                elif session.get_gate_data("proxy"):
                    print(json.dumps(TLSProxy.prepare(session, dir), indent=2))
            else:
                logging.errod("Bad sessionid")
                sys.exit(2)
        else:
            logging.error("Use prepare-client-session sessionid directory")
            sys.exit(1)

    else:
        print("Bad command!")
        p.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
