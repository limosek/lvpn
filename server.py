#!/usr/bin/python3

import os
import sys
import time

from lib.signverify import Sign, Verify
from lib.wizard import Wizard

os.environ["NO_KIVY"] = "1"

from lib.authids import AuthIDs
from lib.queue import Queue
from lib.shared import Messages
from lib.vdp import VDP
from server.proxy import Proxy
from server.http import Manager
import logging
import configargparse
import multiprocessing


def loop(queue, mngr_queue, proxy_queue):
    should_exit = False
    while not should_exit:
        if not queue.empty():
            msg = queue.get()
            if Messages.is_for_main(msg):
                if msg == Messages.EXIT:
                    should_exit = True
                    logging.getLogger("client").warning("Exit requested, exiting")
                    break
            elif Messages.is_for_all(msg):
                proxy_queue.put(msg)
                mngr_queue.put(msg)
            elif Messages.is_for_proxy(msg):
                proxy_queue.put(msg)
            else:
                logging.getLogger("client").warning("Unknown msg %s requested, exiting" % msg)
                should_exit = True
                break


def main():
    if not os.getenv("WLS_CFG_DIR"):
        os.environ["WLS_CFG_DIR"] = "/etc/lvpn"
    p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/server.conf'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path', env_var='WLS_CONFIG')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING',
                   env_var='WLS_LOGLEVEL')
    p.add_argument("--haproxy-cfg", help="HAProxy config file to generate",
                   default=os.getenv("WLS_CFG_DIR") + "/haproxy/haproxy.cfg")
    p.add_argument("--var-dir", help="Var directory", default=os.path.expanduser("~") + "/lvpn", env_var="WLS_VAR_DIR")
    p.add_argument("--cfg-dir", help="Cfg directory", default=os.getenv("WLS_CFG_DIR"), env_var="WLS_CONF_DIR")
    p.add_argument("--app-dir", help="App directory", default=os.path.basename(__file__))
    p.add_argument("--haproxy-mgmt", help="HAProxy mgmt sock to use", default="/var/run/haproxy/mgmt")
    p.add_argument("--http-port", help="HTTP port to use", default=8123)
    p.add_argument("--provider-private-key", help="Private provider key",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.private")
    p.add_argument("--provider-public-key", help="Public provider key",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.public")
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/spaces")
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/gates")
    p.add_argument("--authids-dir", help="Directory containing all authids",
                   default=os.getenv("WLS_CFG_DIR") + "/authids")
    p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/providers")
    p.add_argument("--ca-dir", help="Directory for Certificate authority",
                   default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ca"))
    p.add_argument("--ca-name", help="Common name for CA creation",
                   default="LVPN-easy-provider")


    cfg = p.parse_args()
    logging.basicConfig(level=cfg.l)
    cfg.vdp = VDP(cfg)
    cfg.authids = AuthIDs(cfg.authids_dir)
    processes = {}

    Wizard().files(cfg, os.environ["WLS_CFG_DIR"])

    if not os.path.exists(cfg.ca_dir):
        Wizard().ca(cfg)

    if not os.path.exists(cfg.provider_public_key):
        Wizard().provider(cfg)

    if not cfg.provider_public_key or not cfg.provider_private_key:
        logging.error("You need to set provider public and private key")
        sys.exit(1)
    if not os.path.exists(cfg.provider_public_key) or not os.path.exists(cfg.provider_private_key):
        logging.error("You need to set provider public and private key")
        sys.exit(1)
    try:
        Sign(cfg.provider_private_key).sign("test")
    except Exception as e:
        logging.error(e)
        sys.exit(1)
    public = Verify(cfg.provider_public_key).key()
    if not public in cfg.vdp.provider_ids():
        Wizard().provider_vdp(cfg)

    ctrl = multiprocessing.Manager().dict()
    ctrl["cfg"] = cfg
    queue = Queue(multiprocessing.get_context(), "general")
    proxy_queue = Queue(multiprocessing.get_context(), "proxy")
    mngr_queue = Queue(multiprocessing.get_context(), "mngr")

    proxy = multiprocessing.Process(target=Proxy.run, args=[ctrl, queue, proxy_queue], name="ProxyManager")
    proxy.start()
    processes["proxy"] = proxy
    #wallet = multiprocessing.Process(target=ServerWallet.run, args=[ctrl, queue, proxy_queue], name="Wallet")
    #wallet.start()
    #processes["wallet"] = proxy

    pl = multiprocessing.Process(target=loop, args=[queue, mngr_queue, proxy_queue])
    pl.start()

    Manager.run(ctrl, queue, mngr_queue)

    logging.getLogger().warning("Waiting for subprocesses to exit")
    for p in processes.values():
        p.join(timeout=1)
    for p in processes.values():
        p.kill()
        while p.is_alive():
            time.sleep(0.1)
    time.sleep(3)


# Run the Flask application
if __name__ == '__main__':
    main()
