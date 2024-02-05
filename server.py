#!/usr/bin/python3

import os
import sys
import time
import logging

import _queue
import configargparse
import multiprocessing
import stripe

os.environ["NO_KIVY"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"

from lib.signverify import Sign, Verify
from lib.wizard import Wizard
from lib.sessions import Sessions
from lib.queue import Queue
from lib.shared import Messages
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
    p = configargparse.ArgParser(default_config_files=[os.environ["WLS_CFG_DIR"] + '/server.ini'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path', env_var='WLS_CONFIG')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING',
                   env_var='WLS_LOGLEVEL')
    p.add_argument("--log-file", help="Log file")
    p.add_argument("--haproxy-cfg", help="HAProxy config file to generate",
                   default=os.getenv("WLS_CFG_DIR") + "/haproxy/haproxy.cfg")
    p.add_argument("--var-dir", help="Var directory", default=os.path.expanduser("~") + "/lvpn", env_var="WLS_VAR_DIR")
    p.add_argument("--cfg-dir", help="Cfg directory", default=os.getenv("WLS_CFG_DIR"), env_var="WLS_CONF_DIR")
    p.add_argument("--app-dir", help="App directory", default=os.path.dirname(__file__))
    p.add_argument("--tmp-dir", help="Temp directory", default=os.path.expanduser("~") + "/lvpn/tmp", env_var="WLS_TMP_DIR")
    p.add_argument("--haproxy-mgmt", help="HAProxy mgmt sock to use", default="/var/run/haproxy/mgmt")
    p.add_argument("--stripe-api-key", help="Stripe private key for payments")
    p.add_argument("--stripe-plink-id", help="Stripe payment link id for payment")
    p.add_argument("--lthn-price", help="Price for 1 LTHN. Use fixed number for fixed price or use *factor to factor actual price by number")
    p.add_argument("--tradeogre-api-key", help="TradeOgre API key for conversions")
    p.add_argument("--tradeogre-api-secret", help="TradeOgre API secret key for conversions")
    p.add_argument("--http-port", help="HTTP port to use for manager", default=8123)
    p.add_argument('--daemon-host', help='Daemon host', default='localhost')
    p.add_argument('--wallet-rpc-bin', help='Wallet RPC binary file', default="lethean-wallet-rpc")
    p.add_argument('--wallet-cli-bin', help='Wallet CLI binary file', default="lethean-wallet-cli")
    p.add_argument('--wallet-rpc-url', help='Wallet RPC URL', default='http://localhost:1444/json_rpc')
    p.add_argument('--wallet-rpc-port', help='Wallet RPC port', type=int, default=1444)
    p.add_argument('--wallet-rpc-user', help='Wallet RPC user', default='vpn')
    p.add_argument('--wallet-rpc-password', help='Wallet RPC password.', required=True)
    p.add_argument('--wallet-address', help='Wallet public address')
    p.add_argument("--coin-unit", help="Coin minimal unit", type=float, default=1e-8)
    p.add_argument("--provider-private-key", help="Private provider key",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.private")
    p.add_argument("--provider-public-key", help="Public provider key",
                   default=os.getenv("WLS_CFG_DIR") + "/provider.public")
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/spaces")
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/gates")
    p.add_argument("--sessions-dir", help="Directory containing all sessions",
                   default=os.getenv("WLS_CFG_DIR") + "/sessions")
    p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                   default=os.getenv("WLS_CFG_DIR") + "/providers")
    p.add_argument("--ca-dir", help="Directory for Certificate authority",
                   default=os.path.abspath(os.getenv("WLS_CFG_DIR") + "/ca"))
    p.add_argument("--ca-name", help="Common name for CA creation",
                   default="LVPN-easy-provider")
    p.add_argument("--unpaid-expiry", help="Unpaid sessions will expire after this seconds",
                   default=3600, type=int)
    p.add_argument('--force-manager-url', help='Manually override manager url for all spaces. Used just for tests')
    p.add_argument('--force-manager-wallet',
                   help='Manually override wallet address url for all spaces. Used just for tests')

    cfg = p.parse_args()
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
    cfg.vdp = VDP(cfg)
    cfg.sessions = Sessions(cfg)
    processes = {}

    Wizard().files(cfg)

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
    stripe_queue = Queue(multiprocessing.get_context(), "stripe")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    mngr_queue = Queue(multiprocessing.get_context(), "mngr")

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
                stripe_queue.put(msg)
            elif Messages.is_for_wallet(msg):
                wallet_queue.put(msg)
            else:
                logging.getLogger("server").warning("Unknown msg %s requested, exiting" % msg)
                should_exit = True
                break

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
