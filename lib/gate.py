import json
import logging
import os
import sys
import tempfile

from lib.vdpobject import VDPObject


class Gateway(VDPObject):

    def __init__(self, gwinfo):
        try:
            self._data = gwinfo
            if "filetype" in self._data and self._data["filetype"] == 'LetheanGateway':
                pass
            else:
                logging.error("Bad Gateway definition: %s" % gwinfo)
                sys.exit(1)
        except Exception as e:
            logging.error("Bad Gateway definition: %s(%s)" % (gwinfo, e))
            sys.exit(1)

    def get_id(self):
        return self._data["gateid"]

    def get_endpoint(self):
        return "%s:%s" % (self._data[self.get_type()]["host"], self._data[self.get_type()]["port"])

    def is_for_space(self, spaceid):
        if spaceid in self._data["spaces"]:
            return True
        else:
            return False

    def save(self, gates_dir):
        fname = "%s/%s.lgate" % (gates_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def __repr__(self):
        return("Gateway %s/%s" % (self._data["gateid"], self._data["name"]))
