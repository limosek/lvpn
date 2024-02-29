#!/usr/bin/python3
import atexit
import os
import sys
import threading
import time
import logging
import _queue
import configargparse
import multiprocessing

from lib.util import Util

os.environ["NO_KIVY"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

from lib.sessions import Sessions
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
from lib.registry import Registry
from server.wg_service import WGServerService
import lib


def cleanup(queues, processes):
    for q in queues:
        try:
            q.put(Messages.EXIT)
        except Exception as e:
            continue

    logging.getLogger("server").warning("Waiting for subprocesses to exit")
    for p in processes.values():
        p.join(timeout=1)
    for p in processes.values():
        p.kill()
        while p.is_alive():
            time.sleep(0.1)
    time.sleep(3)


def main():
    def refresh_sessions():
        while not should_exit:
            sessions = Sessions()
            sessions.refresh_status()
            logging.warning(repr(sessions))
            time.sleep(10)

    if not os.getenv("WLS_CFG_DIR"):
        os.environ["WLS_CFG_DIR"] = "/etc/lvpn"
    if not os.getenv("WLS_VAR_DIR"):
        os.environ["WLS_VAR_DIR"] = os.path.expanduser("~") + "/lvpn"

    p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/server.ini'])
    p = SharedArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__),
                               "WLS", "server")
    p = ServerArguments.define(p, os.environ["WLS_CFG_DIR"], os.environ["WLS_VAR_DIR"], os.path.dirname(__file__))

    cfg = p.parse_args()
    cfg.is_client = False
    cfg.is_server = True
    cfg.l = cfg.log_level
    if not cfg.log_file:
        cfg.log_file = cfg.var_dir + "/lvpn-server.log"
    if not cfg.audit_file:
        cfg.audit_file = cfg.var_dir + "/lvpn-audit.log"
    fh = logging.FileHandler(cfg.log_file)
    fh.setLevel(cfg.l)
    sh = logging.StreamHandler()
    sh.setLevel(cfg.l)
    formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET, handlers=[fh, sh])
    fh = logging.FileHandler(cfg.audit_file)
    fh.setLevel("DEBUG")
    sh = logging.StreamHandler()
    sh.setLevel("DEBUG")
    formatter = logging.Formatter('AUDIT:%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.getLogger("audit").addHandler(fh)
    logging.getLogger("audit").addHandler(sh)
    if not cfg.wallet_rpc_password:
        logging.getLogger("server").error("Missing Wallet RPC password! Payments will not be processed!")
    processes = {}

    Registry.init(cfg, {}, None)
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

    cfg.vdp = VDP()
    if cfg.readonly_providers:
        cfg.readonly_providers = cfg.readonly_providers.split(",")
    else:
        cfg.readonly_providers = []
        my_providers = cfg.vdp.providers("", my_only=True)
        for m in my_providers:
            cfg.readonly_providers.append(m.get_id())

    if len(cfg.vdp.providers(my_only=True)) == 0:
        logging.error("There is no local provider VDP! Exiting.")
        sys.exit(2)

    ctrl = multiprocessing.Manager().dict()
    Registry.init(cfg, ctrl, cfg.vdp)
    ctrl["cfg"] = cfg
    Messages.init_ctrl(ctrl)
    queue = Queue(multiprocessing.get_context(), "general")
    stripe_queue = Queue(multiprocessing.get_context(), "stripe")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    mngr_queue = Queue(multiprocessing.get_context(), "mngr")
    queues = [queue, stripe_queue, wallet_queue, mngr_queue]
    atexit.register(cleanup, queues, processes)

    if cfg.stripe_api_key:
        stripemngr = multiprocessing.Process(target=StripeManager.run, args=[ctrl, queue, stripe_queue], name="StripeManager")
        stripemngr.start()
        processes["stripemngr"] = stripemngr

    if cfg.wallet_rpc_password:
        wallet = multiprocessing.Process(target=ServerWallet.run, args=[ctrl, queue, wallet_queue], kwargs={"norun": True}, name="ServerWallet")
        wallet.start()
        processes["wallet"] = wallet
    else:
        wallet = False

    if cfg.enable_wg:
        for gate in cfg.vdp.gates():
            if gate.get_type() == "wg":
                wg_queue = Queue(multiprocessing.get_context(), gate.get_id())
                wg = multiprocessing.Process(target=WGServerService.run, args=[ctrl, queue, wg_queue],
                                             kwargs={"gate": gate, "space": None}, name="WGService-%s" % gate.get_id())
                wg.start()
                processes[gate.get_id()] = wg
                queues.append(wg_queue)
    else:
        wg = False

    manager = multiprocessing.Process(target=Manager.run, args=[ctrl, queue, mngr_queue], name="Manager")
    manager.start()
    processes["manager"] = manager

    should_exit = False
    refresh = threading.Thread(target=refresh_sessions)
    refresh.start()

    while not should_exit:
        logging.getLogger("server").debug("Main loop")
        for p in processes.keys():
            if not processes[p].is_alive():
                should_exit = True
                logging.getLogger("server").error(
                    "One of child process (%s,pid=%s) exited. Exiting too" % (p, processes[p].pid))
                break
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                should_exit = True
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
                if wallet:
                    wallet_queue.put(msg)
                mngr_queue.put(msg)
                if cfg.stripe_api_key:
                    stripe_queue.put(msg)
            elif Messages.is_for_wallet(msg):
                if wallet:
                    wallet_queue.put(msg)
            else:
                logging.getLogger("server").warning("Unknown msg %s requested, exiting" % msg)
                should_exit = True
                break

    refresh.join()
    cleanup(queues, processes)


# Run the Flask application
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
