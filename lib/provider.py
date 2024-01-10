import json
import logging
import sys

from lib.vdpobject import VDPObject, VDPException


class Provider(VDPObject):

    def __init__(self, cfg, providerinfo):
        self.cfg = cfg
        try:
            self._data = providerinfo
            if "filetype" in self._data and self._data["filetype"] == 'LetheanProvider' and "ca" in self._data and "wallet" in self._data and "manager-url" in self._data:
                pass
            else:
                logging.error("Bad Provider definition: %s" % providerinfo)
                sys.exit(1)
        except Exception as e:
            logging.error("Bad Provider definition: %s(%s)" % (providerinfo, e))
            raise VDPException("Bad Provider definition: %s(%s)" % (providerinfo, e))

    def get_id(self):
        return self._data["providerid"]

    def get_ca(self):
        return self._data["ca"]

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        fname = "%s/%s.lprovider" % (self.cfg.providers_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def __repr__(self):
        return "Provider %s/%s" % (self._data["providerid"], self._data["name"])
