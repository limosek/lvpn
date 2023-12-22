import glob
import json
import logging
import sys
import requests
import urllib3

from lib.gate import Gateway
from lib.space import Space


class VDP:

    def __init__(self, vdpfile=None, gates_dir=None, spaces_dir=None):
        self._gates = {}
        self._spaces = {}
        if vdpfile:
            data = urllib3.util.parse_url(vdpfile)
            if data.scheme:
                r = requests.Request(vdpfile)
                jsn = r.data
            else:
                with open(vdpfile, "r") as f:
                    jsn = f.read(1000000000)
            try:
                self._data = json.loads(jsn)
                if "filetype" in self._data and self._data["filetype"] == 'VPNDescriptionProtocol':
                    if "gates" in self._data:
                        for g in self._data["gates"]:
                            gt = Gateway(g)
                            self._gates[gt.get_id()] = gt
                    if "spaces" in self._data:
                        for s in self._data["spaces"]:
                            spc = Space(s)
                            self._spaces[spc.get_id()] = spc
                else:
                    logging.error("Bad VDP file %s" % vdpfile)
                    sys.exit(1)

            except Exception as e:
                raise
        elif gates_dir and spaces_dir:
            for gwf in glob.glob(gates_dir + "/*lgate"):
                with open(gwf, "r") as f:
                    jsn = f.read(1000000000)
                    gw = Gateway(json.loads(jsn))
                    self._gates[gw.get_id()] = gw
            for spacef in glob.glob(spaces_dir + "/*lspace"):
                with open(spacef, "r") as f:
                    jsn = f.read(1000000000)
                    spc = Space(json.loads(jsn))
                    self._spaces[spc.get_id()] = spc

        else:
            logging.error("Need spaces directory and gates directory")
            sys.exit(1)
        self._json = json.dumps({
            "filetype": "VPNDescriptionProtocol",
            "version": "1.0",
            "spaces": json.loads(self.spaces(as_json=True)),
            "gates": json.loads(self.gates(as_json=True))
        })
        logging.getLogger("vdp").warning("%s gates and %s spaces available" % (len(self._gates), len(self._spaces)))

    def gates(self, filter="", spaceid=None, as_json=False):
        """Return all gates"""
        gates = []
        for g in self._gates.values():
            if (filter=="") or g.get_json().find(filter) >= 0:
                if spaceid:
                    if g.is_for_space(spaceid):
                        if as_json:
                            gates.append(g.get_dict())
                        else:
                            gates.append(g)
                else:
                    if as_json:
                        gates.append(g.get_dict())
                    else:
                        gates.append(g)
        if as_json:
            return json.dumps(gates)
        else:
            return gates

    def spaces(self, filter="", as_json=False):
        spaces = []
        for s in self._spaces.values():
            if (filter=="") or s.get_json().find(filter) >= 0:
                if as_json:
                    spaces.append(s.get_dict())
                else:
                    spaces.append(s)
        if as_json:
            return json.dumps(spaces)
        else:
            return spaces

    def get_json(self):
        return self._json

    def gate_ids(self):
        return self._gates.keys()

    def space_ids(self):
        return self._spaces.keys()

    def get_gate(self, gwid):
        if gwid in self._gates:
            return self._gates[gwid]
        else:
            return None

    def get_space(self, spaceid):
        if spaceid in self._spaces:
            return self._spaces[spaceid]
        else:
            return None

    def toJson(self):
        return self.get_json()

    def save(self, gates_dir, spaces_dir):
        for g in self.gate_ids():
            go = self.get_gate(g)
            go.save(gates_dir)
        for s in self.space_ids():
            so = self.get_space(s)
            so.save(spaces_dir)
