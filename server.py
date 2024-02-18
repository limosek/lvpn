#!/usr/bin/python3

import os
import sys
import time
import logging
import _queue
import configargparse
import multiprocessing

os.environ["NO_KIVY"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

from lib.sessions import Sessions
from lib.util import Util
from lib.arguments import SharedArguments
from server.arguments import ServerArguments
from lib.signverify import Sign, Verify
from lib.wizard import Wizard
from lib.queue import Queue
from lib.messages import Messages
from lib.vdp import VDP
from server.http import Manager
from server.stripe import StripeManager
from server.wallet import ServerWallet


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
    if not os.getenv("WLS_VAR_DIR"):
        os.environ["WLS_VAR_DIR"] = os.path.expanduser("~") + "/lvpn"

    p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/server.ini'])
    p = SharedArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__),
                               "WLS", "server")
    p = ServerArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__))

    cfg = p.parse_args()
    cfg.l = cfg.log_level
    if not cfg.log_file:
        cfg.log_file = cfg.var_dir + "/lvpn-server.log"
    fh = logging.FileHandler(cfg.log_file)
    fh.setLevel(cfg.l)
    sh = logging.StreamHandler()
    sh.setLevel(cfg.l)
    formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET, handlers=[fh, sh])
    cfg.readonly_providers = cfg.readonly_providers.split(",")
    processes = {}

    Wizard().files(cfg)

    if not os.path.exists(cfg.ca_dir):
        Wizard().ca(cfg)

    if not os.path.exists(cfg.ssh_user_ca_private):
        Wizard().ssh_ca(cfg)

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

    cfg.vdp = VDP(cfg)
    ctrl = multiprocessing.Manager().dict()
    ctrl["cfg"] = cfg
    Messages.init_ctrl(ctrl)
    queue = Queue(multiprocessing.get_context(), "general")
    stripe_queue = Queue(multiprocessing.get_context(), "stripe")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    mngr_queue = Queue(multiprocessing.get_context(), "mngr")

    if cfg.stripe_api_key:
        stripemngr = multiprocessing.Process(target=StripeManager.run, args=[ctrl, queue, stripe_queue], name="StripeManager")
        stripemngr.start()
        processes["stripemngr"] = stripemngr
    wallet = multiprocessing.Process(target=ServerWallet.run, args=[ctrl, queue, wallet_queue], kwargs={"norun": True}, name="ServerWallet")
    wallet.start()
    processes["wallet"] = wallet
    manager = multiprocessing.Process(target=Manager.run, args=[ctrl, queue, mngr_queue], name="Manager")
    manager.start()
    processes["manager"] = manager

    should_exit = False
    while not should_exit:
        logging.getLogger("server").debug("Main loop")
        for p in processes.keys():
            if not processes[p].is_alive():
                should_exit = True
                logging.getLogger("server").error(
                    "One of child process (%s,pid=%s) exited. Exiting too" % (p, processes[p].pid))
                break
            time.sleep(1)
        if not queue.empty():
            try:
                msg = queue.get()
            except _queue.Empty:
                continue
            if not msg:
                continue
            if Messages.is_for_main(msg):
                if msg == Messages.EXIT:
                    should_exit = True
                    logging.getLogger("server").warning("Exit requested, exiting")
                    break
            elif Messages.is_for_all(msg):
                wallet_queue.put(msg)
                mngr_queue.put(msg)
                if cfg.stripe_api_key:
                    stripe_queue.put(msg)
            elif Messages.is_for_wallet(msg):
                wallet_queue.put(msg)
            else:
                logging.getLogger("server").warning("Unknown msg %s requested, exiting" % msg)
                should_exit = True
                break
        sessions = Sessions(cfg)
        logging.warning(repr(sessions))

    logging.getLogger("server").warning("Waiting for subprocesses to exit")
    for p in processes.values():
        p.join(timeout=1)
    for p in processes.values():
        p.kill()
        while p.is_alive():
            time.sleep(0.1)
    time.sleep(3)


# Run the Flask application
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
