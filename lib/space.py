import json
import logging
import sys

from lib.vdpobject import VDPObject, VDPException


class Space(VDPObject):

    def __init__(self, cfg, spaceinfo):
        self.cfg = cfg
        try:
            self._data = spaceinfo
            if "filetype" in self._data and self._data["filetype"] == 'LetheanSpace' and "providerid" in self._data:
                pass
            else:
                logging.error("Bad Space definition: %s" % spaceinfo)
                sys.exit(1)
        except Exception as e:
            logging.error("Bad Space definition: %s(%s)" % (spaceinfo, e))
            raise VDPException("Bad Space definition: %s(%s)" % (spaceinfo, e))

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

    def __repr__(self):
        return "Space %s/%s" % (self._data["spaceid"], self._data["name"])
