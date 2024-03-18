import json
import logging
import sys

from lib.registry import Registry
from lib.vdpobject import VDPObject, VDPException


class Provider(VDPObject):

    tpe = 'Provider'

    def __init__(self, providerinfo, file=None):
        self.validate(providerinfo, "Provider", file)
        self._data = providerinfo
        self._local = False
        self._file = file

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

    def __repr__(self):
        if Registry.cfg.is_server:
            return "Provider %s/%s[local=%s]" % (self._data["providerid"], self._data["name"], self.is_local())
        else:
            return "Provider %s/%s" % (self._data["providerid"], self._data["name"])
