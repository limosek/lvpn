import json
import logging
import os
import signal
import sys

import requests

from lib.runcmd import RunCmd
from lib.service import ServiceException, Service


class DaemonException(ServiceException):
    pass


class Daemon(Service):

    p = None
    myname = "daemon-rpc"

    @classmethod
    def run(cls, ctrl, queue, myqueue, daemon_host, daemon_port, daemon_rpc_url):
        """
        Static definition to run service. It is called from multiprocessing.
        """
        cls.daemon_host = daemon_host
        cls.daemon_port = daemon_port
        cls.daemon_rpc_url = daemon_rpc_url
        super().run(ctrl, queue, myqueue)

    @classmethod
    def rpc(cls, method, params=None, httpmethod="GET", exc=False):
        if not params:
            params = {}
        payload = json.dumps({"method": method, "params": params})
        headers = {'content-type': "application/json", 'cache-control': "no-cache"}
        try:
            response = requests.request(httpmethod, cls.daemon_rpc_url, data=payload, headers=headers, timeout=10)
            if response.status_code != 200:
                raise DaemonException(code=response.status_code, message=response.content)
            else:
                j = json.loads(response.text)
                if "error" in j:
                    logging.getLogger(cls.myname).error(j)
                    return False
                elif "result" in j:
                    logging.getLogger(cls.myname).debug("Daemon RPC %s result: %s" % (method, j["result"]))
                    return j["result"]
                else:
                    logging.getLogger(cls.myname).error(j)
                    return False
        except Exception as e:
            if exc:
                raise
            else:
                logging.getLogger(cls.myname).error(e)
                return False

    @classmethod
    def get_info(cls, exc=False):
        i = cls.rpc("get_info", exc=exc)
        return i

    @classmethod
    def postinit(cls):
        args = [
            Registry.cfg.daemon_bin,
            "--log-file=%s/daemon.log" % Registry.cfg.var_dir,
            "--data-dir=%s/data" % Registry.cfg.var_dir,
            "--add-exclusive-node=127.0.0.1:48772",
            "--p2p-bind-ip=127.0.0.1",
            "--no-igd"
        ]
        if Registry.cfg.run_daemon:
            logging.getLogger(cls.myname).warning("Running daemon subprocess: %s" % " ".join(args))
            RunCmd.init(Registry.cfg)
            cls.p = RunCmd.popen(args, stdout=sys.stdout, stdin=sys.stdin, cwd=cls.ctrl["tmpdir"], shell=False)

    @classmethod
    def stop(cls):
        cls.exit = True
        if cls.p and not cls.p.returncode:
            logging.getLogger(cls.myname).warning("Killing daemon subprocess with PID %s" % cls.p.pid)
            os.kill(cls.p.pid, signal.SIGINT)
        try:
            if cls.p:
                cls.p.communicate()
        except Exception as e:
            pass
