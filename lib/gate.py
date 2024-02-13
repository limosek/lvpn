import logging
import socket

from lib.vdpobject import VDPObject, VDPException


class Gateway(VDPObject):

    def __init__(self, cfg, gwinfo, file=None):
        self.cfg = cfg
        self.validate(gwinfo, "Gate", file)
        self._data = gwinfo

    def get_id(self):
        return self.get_provider_id() + "." + self._data["gateid"]

    def get_ca(self):
        return self.get_provider().get_ca()

    def get_endpoint(self, resolve=False):
        if not resolve:
            return "%s:%s" % (self._data[self.get_type()]["host"], self._data[self.get_type()]["port"])
        else:
            try:
                ip = socket.gethostbyname(self._data[self.get_type()]["host"])
                return tuple([ip, self._data[self.get_type()]["port"]])
            except socket.error:
                logging.getLogger("vdp").error("Error resolving %s" % self._data[self.get_type()]["host"])
                return tuple([self._data[self.get_type()]["host"], self._data[self.get_type()]["port"]])

    def set_endpoint(self, host, port):
        self._data[self.get_type()]["host"] = host
        self._data[self.get_type()]["port"] = port

    def is_for_space(self, spaceid):
        if spaceid in self._data["spaces"]:
            return True
        else:
            return False

    def is_tls(self):
        if "tls" in self._data[self.get_type()]:
            if self._data[self.get_type()]["tls"]:
                return True
            else:
                return False
        else:
            return True

    def get_wallet(self):
        return self.get_provider().get_wallet()

    def get_local_port(self):
        if self.get_type() == "http-proxy":
            return 8080
        elif self.get_type() == "daemon-rpc-proxy":
            return 48782
        elif self.get_type() == "daemon-p2p-proxy":
            return 48772
        elif self.get_type() == "socks-proxy":
            return 8081
        else:
            return None

    def space_ids(self):
        return self._data["spaces"]

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        fname = "%s/%s.lgate" % (self.cfg.gates_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def get_title(self):
        return self._data["name"]

    def activate(self, session):
        if self.get_type() == "ssh":
            pass
        elif self.get_type() == "http-proxy":
            pass
        return True

    def __repr__(self):
        return "Gateway %s/%s" % (self._data["gateid"], self._data["name"])
