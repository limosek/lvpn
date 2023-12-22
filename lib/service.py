import logging
import time
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
                msg = cls.myqueue.get(block=False, timeout=0.01)
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
        logging.basicConfig(level=cls.ctrl["cfg"].l)
        logging.getLogger(cls.myname).debug("Starting Service %s" % cls.myname)
        try:
            cls.postinit()
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

