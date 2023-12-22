import json
import logging
import time
import threading

from lib.daemon import Daemon
from lib.shared import Messages


class ClientDaemon(Daemon):

    @classmethod
    def update_info(cls):
        last = "No connection"
        while not cls.exit:
            logging.getLogger("daemon").debug("Daemon loop")
            try:
                i = cls.get_info()
                if i and "status" in i and i["status"] == "OK":
                    cls.set_value("daemon_connection", True)
                    cls.set_value("daemon_height", i["height"])
                    if last != "OK":
                        cls.log_message("daemon", "Connected")
                    last = "OK"
                else:
                    cls.set_value("daemon_connection", False)
                    cls.log_message("daemon", "No connection")
                    last = "No connection"
            except Exception as e:
                logging.getLogger(cls.myname).error(e)
            time.sleep(5)

    @classmethod
    def postinit(cls):
        cls.processes = []
        cls.exit = False
        di = threading.Thread(target=cls.update_info)
        cls.processes.append(di)
        for p in cls.processes:
            p.start()

    @classmethod
    def stop(cls):
        cls.exit = True
        for p in cls.processes:
            p.join()
