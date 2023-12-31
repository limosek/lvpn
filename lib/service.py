import logging
import os
import time

import _queue
import setproctitle

from lib.shared import Messages


class ServiceException(Exception):
    def __init__(self, code, message, *args):
        self.code = code
        self.message = message
        super().__init__(*args)

    def __str__(self):
        return "%s: %s %s" % (self.__class__, self.code, self.message)


class Service:
    exit = None
    processes = None
    queue = None
    myqueue = None
    myname = None

    @classmethod
    def loop(cls):
        """ Default loop for every service. """
        while not cls.exit:
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                except _queue.Empty:
                    pass
                if msg == Messages.EXIT:
                    break
            time.sleep(1)

    @classmethod
    def run(cls, ctrl, queue, myqueue, **kwargs):
        """
        Static definition to run service. It is called from multiprocessing.
        """

        if not cls.myname:
            raise NotImplementedError("You cannot use base Service class.")

        cls.ctrl = ctrl
        cls.queue = queue
        cls.myqueue = myqueue
        for handler in logging.getLogger(cls.myname).handlers[:]:
            logging.getLogger(cls.myname).removeHandler(handler)
        fh = logging.FileHandler(cls.ctrl["cfg"].var_dir + "/lvpn-client.log")
        fh.setLevel(cls.ctrl["cfg"].l)
        formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
        fh.setFormatter(formatter)
        logging.getLogger(cls.myname).addHandler(fh)
        logging.getLogger(cls.myname).debug("Starting Service %s" % cls.myname)
        try:
            cls.postinit()
            setproctitle.setproctitle("lvpn-%s" % cls.myname)
            cls.loop()

        except Exception as e:
            cls.stop()
            raise

        cls.stop()

    @classmethod
    def postinit(cls):
        pass

    @classmethod
    def stop(cls):
        logging.getLogger(cls.myname).debug("Stopping Service %s" % cls.myname)
        cls.exit = True
        pass

    @classmethod
    def get_value(cls, name):
        if name in cls.ctrl:
            return cls.ctrl[name]
        else:
            return None

    @classmethod
    def set_value(cls, name, value):
        cls.ctrl[name] = value

    @classmethod
    def log_message(cls, process, value):
        log = cls.get_value("log")
        if not log:
            cls.set_value("log", "")
        log = "\n".join(log.split("\n")[:30])
        log += "%s:%s\n" % (process, value)
        cls.set_value("log", log)

