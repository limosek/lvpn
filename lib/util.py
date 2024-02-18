import codecs
import os
import platform
import random
import time
import socket
from contextlib import closing

from lib.runcmd import RunCmd


class Util:

    @classmethod
    def check_paymentid(cls, paymentid, check_length=True):
        if check_length:
            if len(paymentid) != 16:
                return False
        try:
            codecs.decode(paymentid, "hex")
            return True
        except Exception as e:
            pass
        return False

    @classmethod
    def check_wallet_address(cls, wallet):
        if len(wallet) != 97:
            return False
        if not wallet.startswith("iz"):
            return False
        return True

    @classmethod
    def shorten_wallet_address(cls, wallet):
        return wallet[:5] + "..." + wallet[-10:]

    @classmethod
    def every_x_seconds(cls, x, accuracy=1):
        if int(time.time()) % x < accuracy:
            return True
        else:
            return False

    @classmethod
    def set_key_permissions(cls, file):
        if platform.system() == "Windows":
            RunCmd.get_output(["icacls", file, "/Inheritance:r"])
            RunCmd.get_output(["icacls", file, "/grant:r", "%s:(R)" % os.getenv("UserName")])
        else:
            os.chmod(file, 0o700)

    @classmethod
    def find_free_port(cls):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    @classmethod
    def find_random_free_port(cls, max_iters=100, from_=20000, to_=50000):
        found = False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        iters = 0
        while not found and iters < max_iters:
            try:
                port = random.randint(from_, to_)
                s.bind(("127.0.0.1", port))
                s.close()
                return port
            except socket.error as e:
                iters += 1

    @classmethod
    def test_free_port(cls, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return True
        except socket.error as e:
            return False

