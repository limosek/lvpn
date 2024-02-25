import time

from lib.messages import Messages
from lib.registry import Registry
from lib.service import Service, ServiceException
from lib.wg_engine import WGEngine


class WGService(Service):
    session = None
    myname = "wg_service"

    @classmethod
    def loop1(cls):
        """We must be either client or server"""
        raise NotImplementedError

    @classmethod
    def loop(cls):
        cls.sactive = False
        while not cls.exit:
            cls.log_debug("Loop")
            cls.gathered = WGEngine.gather_wg_data(cls.iface)
            cls.loop1()
            for peer in cls.gathered["peers"]:
                print(peer)
            for i in range(1, 20):
                time.sleep(1)
                if cls.myqueue and not cls.myqueue.empty():
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                    if msg == Messages.EXIT:
                        return
