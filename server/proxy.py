
import logging
import time

from lib.service import Service


class Proxy(Service):

    myname = "proxy-manager"

    @classmethod
    def postinit(cls):
        time.sleep(3600)


