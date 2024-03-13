import json
import multiprocessing
import time

import configargparse
import logging
import nacl.signing
import nacl.encoding
import os
import sys
import ownca
import requests

os.environ["NO_KIVY"] = "1"

from lib.registry import Registry
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


def print_session_row(session):
    print("%s,%s,%s,%s,%s,%s,%s,%s,%s" % (
        session.get_id(),
        session.get_gateid(),
        session.get_spaceid(),
        session.is_active(),
        session.is_free(),
        session.seconds_left(),
        session.is_paid(),
        session.get_price(),
        session.get_contributions_price()
    ))


def main():
    if not os.getenv("WLS_CFG_DIR"):
        os.environ["WLS_CFG_DIR"] = "/etc/lvpn"
    if not os.getenv("WLS_VAR_DIR"):
        os.environ["WLS_VAR_DIR"] = os.path.expanduser("~") + "/lvpn/"
    if not os.getenv("WLC_CFG_DIR"):
        os.environ["WLC_CFG_DIR"] = os.path.expanduser("~") + "/lvpn/"
    if not os.getenv("WLC_VAR_DIR"):
        os.environ["WLC_VAR_DIR"] = os.path.expanduser("~") + "/lvpn/"

    if os.getenv("WLC_CLIENT"):
        p = configargparse.ArgParser(default_config_files=[os.environ["WLC_CFG_DIR"] + '/mgmt.ini'])
        p = SharedArguments.define(p, os.environ["WLC_CFG_DIR"], os.environ["WLC_VAR_DIR"], os.path.dirname(__file__),
                                   "WLC", "client")
        p = ClientArguments.define(p, os.environ["WLC_CFG_DIR"], os.environ["WLC_VAR_DIR"], os.path.dirname(__file__))
    else:
        p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/mgmt.ini'])
        p = SharedArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__),
                                   "WLS", "client")
        p = ServerArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__))

    p.add_argument("--client-mgmt-url", type=str, help="Client management URL", default="http://localhost:8124")
    p.add_argument("--server-mgmt-url", type=str, help="Client management URL", default="http://localhost:8123")
    p.add_argument("cmd", help="Command to be used", type=str, choices={
        "init": "Initialize files",
        "show-vdp": "Print VDP from actual spaces and gates to stdout",
        "push-vdp": "Push VDP to server",
        "fetch-vdp": "Fetch VDP and save locally",
        "refresh-vdp": "Refresh revisions on all local VDP objects",
        "list-providers": "List actual known providers",
        "list-spaces": "List actual known spaces",
        "list-gates": "List actual known gates",
        "list-server-sessions": "List actual server sessions",
        "list-client-sessions": "List actual client sessions",
        "generate-provider-keys": "Generate provider public and private keys",
        "generate-cfg": "Generate config file",
        "sign-text": "Sign text by provider",
        "verify-text": "Verify text signed by provider",
        "issue-crt": "Issue certificate",
        "generate-ca": "Generate certificate authority",
        "generate-vdp": "Generate basic VDP data for provider",
        "request-client-session": "Request session to connect to gate/space",
        "pay-client-session": "Pay requested session",
        "prepare-client-session": "Prepare client files based on sessionid",
        "create-paid-server-session": "Prepare session manually on server"
    })
    p.add_argument("args", help="Args for command", nargs="*")

    cfg = p.parse_args()
    cfg.readonly_providers = []
    cfg.l = cfg.log_level
    logging.basicConfig(level=cfg.l)
    Registry.cfg = cfg
    Registry.cfg.log_file = cfg.var_dir + "/lvpn-mgmt.log"
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
                print("Fetched remote VDP to local database")
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
                    print("Pushed VDP to remote server %s" % vdp.get_provider(cfg.args[0]).get_manager_url())
                    print(json.loads(pushed))
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

    elif cfg.cmd == "refresh-vdp":
        if len(cfg.args) == 0:
            wg = False
        elif len(cfg.args) == 0:
            gateid = cfg.args[0]
            wg = True
            sessions = Sessions().find(gateid=gateid, active=True)
            ip = sessions[0].get_gate_data("wg")["client_ipv4_address"]
        else:
            print("Use refresh-vdp")
            sys.exit(1)
        Registry.cfg.spaces_dir = Registry.cfg.my_spaces_dir
        Registry.cfg.providers_dir = Registry.cfg.my_providers_dir
        Registry.cfg.gates_dir = Registry.cfg.my_gates_dir
        vdp = VDP()
        for g in vdp.gates(my_only=True):
            g.set_as_fresh()
            if wg:
                endpoint = g.get_endpoint()
                endpoint[0] = ip
                g.set_endpoint(ip, endpoint[1])
            g.save(origfile=True)
        for s in vdp.spaces(my_only=True):
            s.set_as_fresh()
            s.save(origfile=True)
        for p in vdp.providers(my_only=True):
            p.set_as_fresh()
            p.save(origfile=True)

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

    elif cfg.cmd == "list-server-sessions":
        m = requests.request("GET", cfg.server_mgmt_url + "/api/sessions", headers={"Authorization": "Bearer %s" % Registry.cfg.manager_bearer_auth})
        if m.status_code == 200:
            sessions = json.loads(m.text)
            print("id,gate,space,active,free,seconds_left,paid,price,contributions_price")
            for s in sessions:
                session = Session(s)
                print_session_row(session)
        else:
            print(m.status_code, m.text)
            sys.exit(2)

    elif cfg.cmd == "list-client-sessions":
        Registry.vdp = VDP()
        m = requests.request("GET", cfg.client_mgmt_url + "/api/sessions", headers={"Authorization": "Bearer %s" % Registry.cfg.manager_bearer_auth})
        if m.status_code == 200:
            sessions = json.loads(m.text)
            print("id,gate,space,active,free,seconds_left,paid,price,contributions_price")
            for s in sessions:
                session = Session(s)
                print_session_row(session)
        else:
            print(m.status_code, m.text)
            sys.exit(2)

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
        if cfg.args and len(cfg.args) == 5:
            name = cfg.args[0]
            space = cfg.args[1]
            fqdn = cfg.args[2]
            wallet = cfg.args[3]
            manager_url = cfg.args[4]
            cfg.providers_dir = cfg.my_providers_dir
            cfg.spaces_dir = cfg.my_spaces_dir
            cfg.gates_dir = cfg.my_gates_dir
            Wizard.provider_vdp(cfg, name,  space, wallet, fqdn, manager_url)
        else:
            logging.error("Need generate-vdp 'name' 'space' 'fqdn' 'wallet' 'manager_url'")
            sys.exit(1)

    elif cfg.cmd == "request-client-session":
        if cfg.args and len(cfg.args) >= 2:
            gateid = cfg.args[0]
            spaceid = cfg.args[1]
            if len(cfg.args) == 3:
                days = int(cfg.args[2])
            else:
                days = None
            cfg.vdp = VDP()
            Registry.vdp = cfg.vdp
            gate = cfg.vdp.get_gate(gateid)
            space = cfg.vdp.get_space(spaceid)
            if gate and space:
                mngr = ManagerRpcCall(Registry.cfg.client_mgmt_url)
                s = mngr.create_session(gate, space, days)
                session = Session(s)
                session.save()
                print(session)
            else:
                logging.error("Unknown gate or space")
                sys.exit(1)
        else:
            logging.error("Use request-session gate space")
            sys.exit(1)

    elif cfg.cmd == "pay-client-session":
        if cfg.args and len(cfg.args) == 1:
            sessionid = cfg.args[0]
            m = requests.request("GET", Registry.cfg.client_mgmt_url + "/api/pay/session/%s" % sessionid)
            print(m.status_code, m.text)
        else:
            logging.error("Use pay-session sessionid")
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

    elif cfg.cmd == "create-paid-server-session":
        s = Session()
        if len(cfg.args) >= 3:
            Registry.vdp = VDP()
            gateid = cfg.args[0]
            spaceid = cfg.args[1]
            days = int(cfg.args[2])
            Registry.cfg.is_server = True
            Registry.cfg.is_client = False
            s.generate(gateid, spaceid, days)
            for arg in cfg.args[3:]:
                try:
                    (attr, value) = arg.split("=")
                    s._data[attr] = value
                except Exception as e:
                    logging.error("Use create-paid-server-session gateid spaceid days attr1=value [attr2=value] ...")
                    sys.exit(3)
            s.validate()
            s.add_payment(s.get_price(), 1234, "manually_paid")
            s.save()
            print(s)
        else:
            logging.error("Use create-paid-server-session gateid spaceid days attr1=value [attr2=value] ...")
            sys.exit(3)

    else:
        print("Bad command!")
        p.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
