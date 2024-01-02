import json
import os
import signal
import subprocess
import logging
import sys
import time

import _queue
import requests
from requests.auth import HTTPDigestAuth

from lib.runcmd import RunCmd
from lib.service import ServiceException, Service
from lib.shared import Messages


class WalletException(ServiceException):
    pass


class Wallet(Service):

    pc = None
    p = None
    myname = "wallet"

    @classmethod
    def rpc(cls, method, params=None, httpmethod="GET", exc=False):
        if not params:
            params = {}
        payload = json.dumps({"method": method, "params": params})
        headers = {'content-type': "application/json", 'cache-control': "no-cache"}
        try:
            response = requests.request(httpmethod, cls.ctrl["cfg"].wallet_rpc_url, data=payload, headers=headers,
                                        auth=HTTPDigestAuth(cls.ctrl["cfg"].wallet_rpc_user,
                                                            cls.ctrl["cfg"].wallet_rpc_password), timeout=10)
            if response.status_code != 200:
                raise WalletException(code=response.status_code, message=response.content)
            else:
                j = json.loads(response.text)
                if "error" in j:
                    if exc:
                        raise WalletException(j["error"]["code"], j["error"]["message"])
                    else:
                        logging.getLogger(cls.myname).error(j)
                        return False
                elif "result" in j:
                    logging.getLogger(cls.myname).debug("Wallet RPC %s result: %s" % (method, j["result"]))
                    return j["result"]
                else:
                    raise WalletException(501, "Bad response %s" % j)
        except requests.exceptions.ConnectionError as e:
            if exc:
                raise WalletException(500, "Connection error %s" % e)
            else:
                logging.getLogger(cls.myname).error(e)
                return False
        except requests.exceptions.ReadTimeout as e:
            logging.getLogger(cls.myname).error(e)
            return False

    @classmethod
    def create(cls):
        w = cls.rpc("create_wallet", {
            "filename": cls.ctrl["cfg"].wallet_name,
            "password": cls.ctrl["cfg"].wallet_password,
            "language": "English"
        }, exc=True)
        return w

    @classmethod
    def open(cls):
        w = cls.rpc("open_wallet", {
            "filename": cls.ctrl["cfg"].wallet_name,
            "password": cls.ctrl["cfg"].wallet_password,
            "language": "English"
        }, exc=True)
        return w

    @classmethod
    def restore(cls, seed):
        args = [
            cls.ctrl["cfg"].wallet_cli_bin,
            "--restore-deterministic-wallet",
            "--generate-new-wallet", "%s/%s" % (cls.ctrl["cfg"].var_dir, cls.ctrl["cfg"].wallet_name),
            "--daemon-address=%s:48782" % (cls.ctrl["cfg"].daemon_host),
            "--log-level=1", "--log-file=%s/wallet.log" % cls.ctrl["cfg"].var_dir,
            "--trusted-daemon",
            "--electrum-seed", seed,
            "--password", cls.ctrl["cfg"].wallet_password,
            "rescan_bc"
        ]
        logging.getLogger("wallet").warning("Running wallet-cli process: %s" % " ".join(args))
        cls.pc = RunCmd.popen(args, cwd=cls.ctrl["tmpdir"], shell=False)

    @classmethod
    def get_balance(cls, walletid=0):
        b = cls.rpc("getbalance", {"account_index": walletid})
        if bool(b):
            return int(b["balance"]) * cls.ctrl["cfg"].coin_unit
        else:
            return False

    @classmethod
    def get_unlocked_balance(cls, walletid=0):
        b = cls.rpc("getbalance", {"account_index": walletid})
        if bool(b):
            return int(b["unlocked_balance"]) * cls.ctrl["cfg"].coin_unit
        else:
            return False

    @classmethod
    def get_height(cls):
        h = cls.rpc("getheight")
        return h

    @classmethod
    def get_address(cls):
        addr = cls.rpc("getaddress", exc=True)
        if addr:
            return addr["address"]
        else:
            return False

    @classmethod
    def loop(cls):
        logging.getLogger("wallet").debug("Wallet loop")
        while not cls.p.poll():
            if cls.pc:
                try:
                    logging.getLogger("wallet").error(cls.pc.communicate(input=b"\n\r\n\r", timeout=1))
                except Exception as e:
                    logging.getLogger("wallet").error(e)
            time.sleep(1)
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                    if not msg:
                        continue
                    if msg.startswith("Wallet/Pay"):
                        data = Messages.get_msg_data(msg)
                        cls.transfer(data["wallet"], data["amount"], data["authid"])
                    elif msg.startswith("Wallet/RestoreFromSeed"):
                        data = Messages.get_msg_data(msg)
                        try:
                            cls.restore(data["seed"])
                            cls.open()
                        except Exception as e:
                            logging.getLogger("wallet").error(e)
                            cls.queue.put(Messages.gui_popup(str(e)))
                    elif msg.startswith("Wallet/Create"):
                        try:
                            try:
                                cls.create()
                            except WalletException as e:
                                cls.queue.put(Messages.gui_popup(str(e)))
                            cls.open()
                        except Exception as e:
                            logging.getLogger("wallet").error(e)
                    elif msg == Messages.EXIT:
                        break
                except _queue.Empty:
                    pass

    @classmethod
    def postinit(cls):
        args = [
            cls.ctrl["cfg"].wallet_rpc_bin,
            "--wallet-dir=%s" % cls.ctrl["cfg"].var_dir,
            "--rpc-login=%s:%s" % (cls.ctrl["cfg"].wallet_rpc_user, cls.ctrl["cfg"].wallet_rpc_password),
            "--rpc-bind-port=%s" % (cls.ctrl["cfg"].wallet_rpc_port),
            "--daemon-address=%s:48782" % (cls.ctrl["cfg"].daemon_host),
            "--log-level=1", "--log-file=%s/wallet.log" % cls.ctrl["cfg"].var_dir,
            "--trusted-daemon"
        ]
        logging.getLogger("wallet").warning("Running wallet subprocess: %s" % " ".join(args))
        RunCmd.init(cls.ctrl["cfg"])
        cls.p = RunCmd.popen(args, stdout=sys.stdout, stdin=sys.stdin, cwd=cls.ctrl["tmpdir"], shell=False)
        cls.pc = None

    @classmethod
    def transfer(cls, wallet, price, authid):
        data = cls.rpc("transfer_split",
                {
                    "destinations": [ {"amount": int(float(price) / cls.ctrl["cfg"].coin_unit), "address": wallet} ],
                    "payment_id": authid
                }, "POST")

    @classmethod
    def stop(cls):
        cls.exit = True
        if cls.p and not cls.p.returncode:
            logging.getLogger(cls.myname).warning("Killing wallet subprocess with PID %s" % cls.p.pid)
            os.kill(cls.p.pid, signal.SIGINT)
        if cls.pc and not cls.pc.returncode:
            logging.getLogger(cls.myname).warning("Killing wallet-cli subprocess with PID %s" % cls.pc.pid)
            os.kill(cls.pc.pid, signal.SIGINT)
        try:
            if cls.p:
                cls.p.communicate()
            if cls.pc:
                cls.pc.communicate()
        except Exception as e:
            pass
