import datetime
import logging
import multiprocessing
import signal
import sys
import time
import _queue
import setproctitle

from lib.messages import Messages
from lib.registry import Registry


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
    cfg = None

    @classmethod
    def loop(cls):
        """ Default loop for every service. """
        while not cls.exit:
            if cls.myqueue and not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                    if msg == Messages.EXIT:
                        break
                except _queue.Empty:
                    pass
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                return

    @classmethod
    def run(cls, ctrl, queue, myqueue, *args, **kwargs):
        """
        Static definition to run service. It is called from multiprocessing.
        """

        if not cls.myname:
            raise NotImplementedError("You cannot use base Service class.")

        cls.ctrl = ctrl
        if multiprocessing.parent_process():
            Registry.cfg = ctrl["cfg"]
            Registry.vdp = ctrl["vdp"]
        cls.queue = queue
        cls.myqueue = myqueue
        cls.args = args
        cls.kwargs = kwargs
        logging.getLogger("db").setLevel(Registry.cfg.l)
        logging.getLogger(cls.myname).debug("Starting Service %s" % cls.myname)
        try:
            if Registry.cfg.is_client:
                setproctitle.setproctitle("lvpnc-%s" % cls.myname)
            else:
                setproctitle.setproctitle("lvpns-%s" % cls.myname)
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
    def log_gui(cls, process, value):
        log = cls.get_value("log")
        cls.log_info("%s:%s" % (process, value))
        log.append("%s:%s:%s" % (datetime.datetime.isoformat(datetime.datetime.now()), process, value))
        if len(log) > 30:
            log = log[:30]
        cls.set_value("log", log)

    @classmethod
    def sigterm(cls, sig, frame):
        cls.log_warning("Catched signal %s" % sig)
        cls.stop()
        sys.exit()

    @classmethod
    def log_debug(cls, *args, **kwargs):
        logging.getLogger(cls.myname).debug(*args, **kwargs)

    @classmethod
    def log_info(cls, *args, **kwargs):
        logging.getLogger(cls.myname).info(*args, **kwargs)

    @classmethod
    def log_warning(cls, *args, **kwargs):
        logging.getLogger(cls.myname).warning(*args, **kwargs)

    @classmethod
    def log_error(cls, *args, **kwargs):
        logging.getLogger(cls.myname).error(*args, **kwargs)


