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
from lib.sessions import Sessions
from lib.messages import Messages
from lib.util import Util


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
            response = requests.request(httpmethod, cls.cfg.wallet_rpc_url, data=payload, headers=headers,
                                        auth=HTTPDigestAuth(cls.cfg.wallet_rpc_user,
                                                            cls.cfg.wallet_rpc_password), timeout=10)
            if response.status_code != 200:
                raise WalletException(code=response.status_code, message=response.content)
            else:
                j = json.loads(response.text)
                if "error" in j:
                    if exc:
                        raise WalletException(j["error"]["code"], j["error"]["message"])
                    else:
                        cls.log_error(j)
                        return False
                elif "result" in j:
                    cls.log_debug("Wallet RPC %s result: %s" % (method, j["result"]))
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
            "filename": cls.cfg.wallet_name,
            "password": cls.cfg.wallet_password,
            "language": "English"
        }, exc=True)
        return w

    @classmethod
    def open(cls):
        w = cls.rpc("open_wallet", {
            "filename": cls.cfg.wallet_name,
            "password": cls.cfg.wallet_password,
            "language": "English"
        }, exc=True)
        return w

    @classmethod
    def restore(cls, seed):
        args = [
            cls.cfg.wallet_cli_bin,
            "--restore-deterministic-wallet",
            "--generate-new-wallet", "%s/%s" % (cls.cfg.var_dir, cls.cfg.wallet_name),
            "--daemon-address=%s:48782" % (cls.cfg.daemon_host),
            "--log-level=1", "--log-file=%s/wallet.log" % cls.cfg.var_dir,
            "--trusted-daemon",
            "--electrum-seed", seed,
            "--password", cls.cfg.wallet_password,
            "rescan_bc"
        ]
        logging.getLogger("wallet").warning("Running wallet-cli process: %s" % " ".join(args))
        cls.pc = RunCmd.popen(args, cwd=cls.cfg.tmpdir, shell=False)

    @classmethod
    def get_balance(cls, walletid=0):
        b = cls.rpc("getbalance", {"account_index": walletid})
        if bool(b):
            return int(b["balance"]) * cls.cfg.coin_unit
        else:
            return False

    @classmethod
    def get_unlocked_balance(cls, walletid=0):
        b = cls.rpc("getbalance", {"account_index": walletid})
        if bool(b):
            return int(b["unlocked_balance"]) * cls.cfg.coin_unit
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
    def refresh(cls):
        data = cls.rpc("refresh")
        return data

    @classmethod
    def get_in_transfers(cls, min_height):
        data = cls.rpc("get_transfers", {
            "in": True,
            "min_height": min_height,
            "pool": cls.cfg.use_tx_pool
        })
        return data

    @classmethod
    def loop(cls):
        logging.getLogger(cls.myname).debug("Wallet loop")
        skew = 20000
        while "norun" in cls.kwargs or not cls.p.poll():
            if cls.pc:
                try:
                    logging.getLogger(cls.myname).error(cls.pc.communicate(input=b"\n\r\n\r", timeout=1))
                except Exception as e:
                    logging.getLogger(cls.myname).error(e)
            time.sleep(1)
            if Util.every_x_seconds(10):
                sessions = Sessions(cls.cfg)
                in_transfers = []
                height = cls.get_height()
                matched = 0
                if bool(height):
                    height = height["height"]
                    transfers = cls.get_in_transfers(height - skew)
                    if transfers and "in" in transfers:
                        in_transfers = transfers["in"]
                        for transfer in transfers["in"]:
                            processed = sessions.process_payment(transfer["payment_id"], transfer["amount"] * cls.cfg.coin_unit, transfer["height"], transfer["txid"])
                            if len(processed) > 0:
                                cls.log_warning("Updated %s sessions for payment: txid=%s,amount=%s" % (len(processed), transfer["txid"], transfer["amount"] * cls.cfg.coin_unit))
                                matched += len(processed)
                    skew = 100
                else:
                    logging.getLogger("wallet").error("Cannot get height. Continuing")
                    height = False
                cls.log_info("Inspected wallet payments, from_height=%s, to_height=%s,transfers=%s, updated=%s" % (height - skew, height, len(in_transfers), matched))
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                    if not msg:
                        continue
                    if msg.startswith("Wallet/Pay"):
                        data = Messages.get_msg_data(msg)
                        if cls.transfer(data[0], data[1]):
                            cls.queue.put(Messages.paid(msg))
                        else:
                            cls.queue.put(Messages.unpaid(msg))

                    elif msg.startswith("Wallet/RestoreFromSeed"):
                        data = Messages.get_msg_data(msg)
                        try:
                            cls.restore(data["seed"])
                            cls.open()
                        except Exception as e:
                            logging.getLogger("wallet").error(e)
                            cls.queue.put(Messages.gui_popup(str(e)))
                            cls.log_gui("wallet", "Error restoring wallet: %s" % e)
                    elif msg.startswith("Wallet/Create"):
                        try:
                            try:
                                cls.create()
                            except WalletException as e:
                                cls.queue.put(Messages.gui_popup(str(e)))
                            cls.open()
                        except Exception as e:
                            cls.log_error("Error creating wallet: %s" % e)
                            cls.log_gui("wallet", "Error creating wallet: %s" % e)
                    elif msg == Messages.EXIT:
                        break
                except _queue.Empty:
                    pass

    @classmethod
    def postinit(cls):
        if "norun" in cls.kwargs:
            return
        else:
            args = [
                cls.cfg.wallet_rpc_bin,
                "--wallet-dir=%s" % cls.cfg.var_dir,
                "--rpc-login=%s:%s" % (cls.cfg.wallet_rpc_user, cls.cfg.wallet_rpc_password),
                "--rpc-bind-port=%s" % (cls.cfg.wallet_rpc_port),
                "--daemon-address=%s:48782" % (cls.cfg.daemon_host),
                "--log-level=1", "--log-file=%s/wallet.log" % cls.cfg.var_dir,
                "--trusted-daemon"
            ]
            logging.getLogger("wallet").warning("Running wallet subprocess: %s" % " ".join(args))
            RunCmd.init(cls.cfg)
            cls.p = RunCmd.popen(args, stdout=sys.stdout, stdin=sys.stdin, cwd=cls.cfg.tmp_dir, shell=False)
            cls.pc = None

    @classmethod
    def transfer(cls, payments, paymentid):
        destinations = []
        msg = "["
        amount = 0
        for p in payments:
            destinations.append(
                {"amount": int(p["amount"] / cls.cfg.coin_unit), "address": p["wallet"]}
            )
            msg += "amount=%s,address=%s " % (p["amount"], p["wallet"])
            amount += p["amount"]
        msg += " paymentid=%s]" % paymentid
        cls.log_warning("Transferring coins start: %s" % msg)
        balance = cls.get_unlocked_balance()
        if balance is False or balance is None:
            cls.log_error("Cannot get balance from wallet")
            cls.log_gui("wallet", "Cannot conntact wallet. Is it syncing?")
            return False
        else:
            if balance < amount:
                cls.log_error("Not enough balance to send (%s, needs %s)" % (balance, amount))
                cls.log_gui("wallet", "Not enough balance to send (%s, needs %s)" % (balance, amount))
                return False
        try:
            cls.rpc("transfer_split",
                    {
                        "destinations": destinations,
                        "payment_id": paymentid
                    }, "POST", exc=True)
            cls.log_warning("Transferring coins finished OK: %s" % msg)
            cls.log_gui("wallet", "Transferring coins finished OK: %s" % msg)
            return True
        except WalletException as e:
            cls.log_warning("Transferring coins error: %s" % e.message)
            cls.log_gui("wallet", "Transferring coins error: %s" % e.message)
            return False

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
