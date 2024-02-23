import json
import logging
import sys

from lib.registry import Registry
from lib.vdpobject import VDPObject, VDPException


class Provider(VDPObject):

    def __init__(self, providerinfo, file=None):
        self.validate(providerinfo, "Provider", file)
        self._data = providerinfo
        self._local = False

    def get_id(self):
        return self._data["providerid"]

    def get_wallet(self):
        if Registry.cfg.force_manager_wallet:
            logging.getLogger("vdp").warning("Using forced provider wallet %s" % Registry.cfg.force_manager_wallet)
            return Registry.cfg.force_manager_wallet
        else:
            return self._data["wallet"]

    def get_ca(self):
        return "\n".join(self._data["ca"])

    def get_manager_url(self):
        if Registry.cfg and Registry.cfg.force_manager_url:
            logging.getLogger("vdp").warning("Using forced manager URL %s" % Registry.cfg.force_manager_url)
            return Registry.cfg.force_manager_url
        return self._data["manager-url"]

    def save(self, cfg=None):
        if cfg:
            Registry.cfg = cfg
        fname = "%s/%s.lprovider" % (Registry.cfg.providers_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def __repr__(self):
        return "Provider %s/%s[local=%s]" % (self._data["providerid"], self._data["name"], self.is_local())
