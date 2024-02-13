import json
import logging
import sys

from lib.vdpobject import VDPObject, VDPException


class Provider(VDPObject):

    def __init__(self, cfg, providerinfo, file=None):
        self.cfg = cfg
        self.validate(providerinfo, "Provider", file)
        self._data = providerinfo

    def get_id(self):
        return self._data["providerid"]

    def get_wallet(self):
        if self.cfg.force_manager_wallet:
            logging.getLogger("vdp").warning("Using forced provider wallet %s" % self.cfg.force_manager_wallet)
            return self.cfg.force_manager_wallet
        else:
            return self._data["wallet"]

    def get_ca(self):
        return "\n".join(self._data["ca"])

    def get_manager_url(self):
        if self.cfg and self.cfg.force_manager_url:
            logging.getLogger("vdp").warning("Using forced manager URL %s" % self.cfg.force_manager_url)
            return self.cfg.force_manager_url
        return self._data["manager-url"]

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        fname = "%s/%s.lprovider" % (self.cfg.providers_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def __repr__(self):
        return "Provider %s/%s" % (self._data["providerid"], self._data["name"])
