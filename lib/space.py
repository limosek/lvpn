import json
import logging
import sys

from lib.vdpobject import VDPObject


class Space(VDPObject):

    def __init__(self, spaceinfo):
        try:
            self._data = spaceinfo
            if "filetype" in self._data and self._data["filetype"] == 'LetheanSpace':
                pass
            else:
                logging.error("Bad Space definition: %s" % spaceinfo)
                sys.exit(1)
        except Exception as e:
            logging.error("Bad Gateway definition: %s(%s)" % (spaceinfo, e))
            sys.exit(1)

    def get_id(self):
        return self._data["spaceid"]

    def save(self, spaces_dir):
        fname = "%s/%s.lspace" % (spaces_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def __repr__(self):
        return("Space %s/%s" % (self._data["spaceid"], self._data["name"]))
