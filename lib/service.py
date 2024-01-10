import logging
import time
import socket
from contextlib import closing
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
    def find_free_port(cls):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    @classmethod
    def loop(cls):
        """ Default loop for every service. """
        while not cls.exit:
            if cls.myqueue and not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                except _queue.Empty:
                    pass
                if msg == Messages.EXIT:
                    break
            time.sleep(1)

    @classmethod
    def run(cls, ctrl, queue, myqueue, *args, **kwargs):
        """
        Static definition to run service. It is called from multiprocessing.
        """

        if not cls.myname:
            raise NotImplementedError("You cannot use base Service class.")

        cls.ctrl = ctrl
        cls.queue = queue
        cls.myqueue = myqueue
        cls.args = args
        cls.kwargs = kwargs
        for handler in logging.getLogger(cls.myname).handlers[:]:
            logging.getLogger(cls.myname).removeHandler(handler)
        fh = logging.FileHandler(cls.ctrl["cfg"].var_dir + "/lvpn-client.log")
        fh.setLevel(cls.ctrl["cfg"].l)
        sh = logging.StreamHandler()
        sh.setLevel(cls.ctrl["cfg"].l)
        formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)
        logging.getLogger(cls.myname).addHandler(fh)
        logging.getLogger(cls.myname).addHandler(sh)
        logging.getLogger(cls.myname).debug("Starting Service %s" % cls.myname)
        try:
            setproctitle.setproctitle("lvpn-%s" % cls.myname)
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
        if not log:
            cls.set_value("log", "")
        log = "\n".join(log.split("\n")[:30])
        log += "%s:%s\n" % (process, value)
        cls.set_value("log", log)

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


