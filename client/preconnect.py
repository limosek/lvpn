import time

from lib.mngrrpc import ManagerRpcCall
from lib.service import Service


class PreConnect(Service):
    """PreConnect to service and prepare payment"""

    myname = "preconnect"

    @classmethod
    def run(cls, ctrl, queue, myqueue, gateid, spaceid, days, *args, **kwargs):
        cls.spaceid = spaceid
        cls.gateid = gateid
        cls.days = days
        super().run(ctrl, queue, myqueue)

    @classmethod
    def postinit(cls):

        cls.mngr = ManagerRpcCall("http://localhost:8123")
        cls.connectinfo = cls.mngr.preconnect(
            {
                "spaceid": cls.spaceid,
                "gateid": cls.gateid,
                "days": cls.days
            })
        pass

    @classmethod
    def loop(cls):
        connected = False
        while not connected:
            time.sleep(1)
            connected = cls.mngr.wait_for_connection(cls.connectinfo)
        pass

