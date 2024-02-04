import glob
import json
import logging
import sys
import requests
import urllib3

from lib.gate import Gateway
from lib.space import Space
from lib.provider import Provider
from lib.vdpobject import VDPException, VDPObject


class VDP:

    def __init__(self, cfg, vdpfile=None, vdpdata=None):
        self._gates = {}
        self._spaces = {}
        self._providers = {}
        self.cfg = cfg
        if vdpfile:
            data = urllib3.util.parse_url(vdpfile)
            if data.scheme:
                r = requests.Request(vdpfile)
                vdpdata = r.data
            else:
                with open(vdpfile, "r") as f:
                    vdpdata = f.read(1000000000)
        if vdpdata or vdpfile:
            if type(vdpdata) is str:
                vdpdata = json.loads(vdpdata)
            try:
                VDPObject.validate(vdpdata, "Vdp", vdpfile)
                self._data = vdpdata
                if "filetype" in self._data and self._data["filetype"] == 'VPNDescriptionProtocol':
                    if "providers" in self._data:
                        for p in self._data["providers"]:
                            prov = Provider(self.cfg, p)
                            self._providers[prov.get_id()] = prov
                    if "spaces" in self._data:
                        for s in self._data["spaces"]:
                            spc = Space(self.cfg, s)
                            if not spc.get_provider_id() in self.provider_ids():
                                raise VDPException("Providerid %s for space %s does not exists!" % (spc.get_provider_id(), spc))
                            self._spaces[spc.get_id()] = spc
                    if "gates" in self._data:
                        for g in self._data["gates"]:
                            gt = Gateway(self.cfg, g)
                            if not gt.get_provider_id() in self.provider_ids():
                                raise VDPException("Providerid %s for gate %s does not exists!" % (g.get_provider_id(), gt))
                            for s in gt.space_ids():
                                if s not in self.space_ids():
                                    raise VDPException("SpaceId %s for gate %s does not exists!" % (s, gt))
                            self._gates[gt.get_id()] = gt
                else:
                    logging.error("Bad VDP file %s" % vdpfile)
                    sys.exit(1)

            except Exception as e:
                raise VDPException(str(e))

        elif self.cfg.gates_dir and self.cfg.spaces_dir:
            for providerf in glob.glob(self.cfg.providers_dir + "/*lprovider"):
                logging.getLogger().info("Loading provider %s" % providerf)
                with open(providerf, "r") as f:
                    jsn = f.read(-1)
                    try:
                        prov = Provider(self.cfg, json.loads(jsn), providerf)
                        self._providers[prov.get_id()] = prov
                    except Exception as e:
                        print("Error loading %s: %s" % (providerf, e))

            for spacef in glob.glob(self.cfg.spaces_dir + "/*lspace"):
                logging.getLogger().info("Loading space %s" % spacef)
                with open(spacef, "r") as f:
                    jsn = f.read(-1)
                    try:
                        spc = Space(self.cfg, json.loads(jsn), spacef)
                        if not spc.get_provider_id() in self.provider_ids():
                            raise VDPException(
                                "Providerid %s for space %s does not exists!" % (spc.get_provider_id(), spc))
                        spc._provider = self._providers[spc.get_provider_id()]
                        self._spaces[spc.get_id()] = spc
                    except Exception as e:
                        print("Error loading %s: %s" % (spacef, e))

            for gwf in glob.glob(self.cfg.gates_dir + "/*lgate"):
                logging.getLogger().info("Loading gate %s" % gwf)
                with open(gwf, "r") as f:
                    jsn = f.read(-1)
                    try:
                        gw = Gateway(self.cfg, json.loads(jsn), gwf)
                        if not gw.get_provider_id() in self.provider_ids():
                            raise VDPException("Providerid %s for gate %s does not exists!" % (gw.get_provider_id(), gw))
                        for s in gw.space_ids():
                            if s not in self._spaces.keys():
                                raise VDPException("SpaceId %s for gate %s does not exists!" % (s, gw))
                        gw._provider = self._providers[gw.get_provider_id()]
                        self._gates[gw.get_id()] = gw
                    except Exception as e:
                        print("Error loading %s: %s" % (gwf, e))

        else:
            logging.error("Need spaces directory and gates directory")
            sys.exit(1)
        self._dict = {
            "filetype": "VPNDescriptionProtocol",
            "version": "1.0",
            "spaces": json.loads(self.spaces(as_json=True)),
            "gates": json.loads(self.gates(as_json=True)),
            "providers": json.loads(self.providers(as_json=True))
        }
        self._json = json.dumps(self._dict, indent=2)
        #VDPObject.validate(self._json, "Vdp", vdpfile)
        logging.getLogger("vdp").warning("%s gates and %s spaces available" % (len(self._gates), len(self._spaces)))

    def gates(self, filter="", spaceid=None, as_json=False, internal=True):
        """Return all gates"""
        gates = []
        for g in self._gates.values():
            if not internal and g.is_internal():
                continue
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

    def providers(self, filter="", as_json=False):
        providers = []
        for s in self._providers.values():
            if (filter=="") or s.get_json().find(filter) >= 0:
                if as_json:
                    providers.append(s.get_dict())
                else:
                    providers.append(s)
        if as_json:
            return json.dumps(providers)
        else:
            return providers

    def get_json(self):
        return self._json

    def get_dict(self):
        return self._dict

    def gate_ids(self):
        return self._gates.keys()

    def space_ids(self):
        return self._spaces.keys()

    def provider_ids(self):
        return self._providers.keys()

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

    def get_provider(self, providerid):
        if providerid in self._providers:
            return self._providers[providerid]
        else:
            return None

    def save(self, cfg=None):
        if cfg:
            self.cfg = cfg
        for g in self.gate_ids():
            go = self.get_gate(g)
            go.save(cfg=cfg)
        for s in self.space_ids():
            so = self.get_space(s)
            so.save(cfg=cfg)
        for p in self.provider_ids():
            po = self.get_provider(p)
            po.save(cfg=cfg)
