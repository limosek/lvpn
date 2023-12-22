import multiprocessing

import client
from client.proxy import Proxy
from lib.authid import AuthID


class Connect:

    def __init__(self, ctrl, gateid, spaceid, authid=None, days=1):
        self._ctrl = ctrl
        self._gate = ctrl["vdp"].get_gate(gateid)
        if not self._gate:
            raise Exception("Unknown gateid")
        self._space = ctrl["vdp"].get_space(spaceid)
        if not self._space:
            raise Exception("Unknown spaceid")
        self._authid = AuthID(gateid=gateid, spaceid=spaceid, authid=authid, days=days)

    def prepare(self):
        tmpdir = self._ctrl["cfg"].tmpdir
        cafile = tmpdir + "/" +self._space.get_id() + self._gate.get_id() + ".crt"
        ca = self._gate.get_ca()
        with open(cafile, "w") as f:
            f.write(ca)

    def run(self):
        if self._gate.get_type == "http-proxy":
            proxy = multiprocessing.Process(target=Proxy.run, args=[self._ctrl, client.gui.GUI.queue, proxy_queue], kwargs=
            {
                "cafile": cfg.endpoint_ca,
                "localrpc": 48782,
                "rpcendpoint": cfg.daemon_proxy_rpc_endpoint
            }, name="Proxy")
            proxy.start()
        else:
            raise Exception("Unknown type")
