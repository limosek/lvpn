import json
import logging
import sys

from lib.vdpobject import VDPObject, VDPException


class Space(VDPObject):

    def __init__(self, cfg, spaceinfo, file=None):
        self.cfg = cfg
        self.validate(spaceinfo, "Space", file)
        self._data = spaceinfo
        self._provider = self.cfg.vdp.get_provider(self._data["providerid"])
        if not self._provider:
            raise VDPException("Unknown providerid %s" % self._data["providerid"])
        self._local = self._provider.is_local()

    def get_id(self):
        return self.get_provider_id() + "." + self._data["spaceid"]

    def get_wallet(self):
        return self.get_provider().get_wallet()

    def set_provider(self, provider):
        self._provider = provider
        self._local = self._provider.is_local()

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        fname = "%s/%s.lspace" % (self.cfg.spaces_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def get_title(self):
        return self._data["name"]

    def activate(self, session):
        return True

    def __repr__(self):
        return "Space %s/%s[local=%s]" % (self._data["spaceid"], self._data["name"], self.is_local())
