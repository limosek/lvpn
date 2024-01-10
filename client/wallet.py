import logging
import time
import threading

from lib.wallet import Wallet, WalletException


class ClientWallet(Wallet):

    @classmethod
    def update_wallet_info(cls):
        last = "None"
        while not cls.exit:
            try:
                j = cls.get_balance()
                if type(j) is float:
                    cls.set_value("wallet_connection", True)
                    cls.set_value("balance", str(j))
                    cls.ctrl["wizard"] = False
                else:
                    cls.set_value("wallet_connection", False)
                    cls.log_gui("wallet", "No connection")
                    last = "No connection or sync in progress"
                j = cls.get_unlocked_balance()
                if type(j) is float:
                    cls.set_value("unlocked_balance", str(j))
                if last != "OK":
                    cls.log_gui("wallet", "Connected")
                last = "OK"
                h = cls.get_height()
                if h:
                    cls.set_value("wallet_height", h["height"])
                a = cls.get_address()
                if a:
                    cls.set_value("wallet_address", a)
            except WalletException as e:
                logging.getLogger("wallet").error(e)
                if e.code == -13:
                    cls.ctrl["no_wallet"] = True
                if last == "OK":
                    cls.log_gui("wallet", "No connection")
                    last = "No connection or sync in progress"
            time.sleep(5)

    @classmethod
    def postinit(cls):
        super().postinit()
        cls.processes = []
        cls.exit = False
        try:
            cls.open()
            cls.set_value("wallet_address", cls.get_address())
        except WalletException as e:
            cls.log_gui("wallet", str(e))
        b = threading.Thread(target=cls.update_wallet_info)
        cls.processes.append(b)
        for p in cls.processes:
            p.start()

    @classmethod
    def stop(cls):
        super().stop()
        cls.exit = True
        if cls.processes:
            for p in cls.processes:
                p.join()
