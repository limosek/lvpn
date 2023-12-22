import json
import logging
import requests

from lib.service import ServiceException, Service


class DaemonException(ServiceException):
    pass


class Daemon(Service):

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
