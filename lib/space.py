import json
import logging
import sys

from lib.vdpobject import VDPObject, VDPException


class Space(VDPObject):

    def __init__(self, cfg, spaceinfo, file=None):
        self.cfg = cfg
        self.validate(spaceinfo, "Space", file)
        self._data = spaceinfo

    def get_id(self):
        return self.get_provider_id() + "." + self._data["spaceid"]

    def get_wallet(self):
        return self.get_provider().get_wallet()

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        fname = "%s/%s.lspace" % (self.cfg.spaces_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def get_title(self):
        return self._data["name"]

    def __repr__(self):
        return "Space %s/%s" % (self._data["spaceid"], self._data["name"])
