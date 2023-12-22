#!/usr/bin/python3

import time

from lib.authids import AuthIDs
from lib.queue import Queue
from lib.shared import Messages
from lib.vdp import VDP
from server.proxy import Proxy
from server.http import Manager
import logging
import configargparse
import multiprocessing

from server.wallet import ServerWallet


def main():
    p = configargparse.ArgParser(default_config_files=['/etc/lthn/server.conf'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path', env_var='WLS_CONFIG')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING',
                   env_var='WLS_LOGLEVEL')
    p.add_argument("--haproxy-cfg", help="HAProxy config file to generate", default="/etc/haproxy/haproxy.cfg")
    p.add_argument("--haproxy-mgmt", help="HAProxy mgmt sock to use", default="/var/run/haproxy/mgmt")
    p.add_argument("--http-port", help="HTTP port to use", default=8123)
    p.add_argument("--provider-private-key", help="Private provider key", default="/etc/lthn/provider.private")
    p.add_argument("--provider-public-key", help="Public provider key", default="/etc/lthn/provider.public")
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs", default="/etc/lthn/spaces")
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs", default="/etc/lthn/gates")
    p.add_argument("--authids-dir", help="Directory containing all authids", default="/etc/lthn/authids")

    cfg = p.parse_args()
    logging.basicConfig(level=cfg.l)
    cfg.vdp = VDP(gates_dir=cfg.gates_dir, spaces_dir=cfg.spaces_dir)
    cfg.authids = AuthIDs(cfg.authids_dir)
    processes = {}

    ctrl = multiprocessing.Manager().dict()
    ctrl["cfg"] = cfg
    queue = Queue(multiprocessing.get_context(), "general")
    proxy_queue = Queue(multiprocessing.get_context(), "proxy")
    mngr_queue = Queue(multiprocessing.get_context(), "mngr")

    mngr = multiprocessing.Process(target=Manager.run, args=[ctrl, queue, mngr_queue], name="HTTPManager")
    mngr.start()
    processes["mngr"] = mngr
    proxy = multiprocessing.Process(target=Proxy.run, args=[ctrl, queue, proxy_queue], name="ProxyManager")
    proxy.start()
    processes["proxy"] = proxy
    #wallet = multiprocessing.Process(target=ServerWallet.run, args=[ctrl, queue, proxy_queue], name="Wallet")
    #wallet.start()
    #processes["wallet"] = proxy

    should_exit = False
    while not should_exit:
        for p in processes.keys():
            if not processes[p].is_alive():
                should_exit = True
                logging.getLogger("client").error(
                    "One of child process (%s,pid=%s) exited. Exiting too" % (p, processes[p].pid))
                mngr_queue.put(Messages.EXIT)
                proxy_queue.put(Messages.EXIT)
                break
            time.sleep(0.1)
            if not queue.empty():
                msg = queue.get()
                print(msg)
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
