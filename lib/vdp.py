import glob
import json
import logging
import sys
import requests
import urllib3

from lib.gate import Gateway
from lib.registry import Registry
from lib.space import Space
from lib.provider import Provider
from lib.vdpobject import VDPException, VDPObject


class VDP:

    def __init__(self, vdpfile=None, vdpdata=None, my_only: bool = False):
        self._gates = {}
        self._spaces = {}
        self._providers = {}
        if vdpfile:
            data = urllib3.util.parse_url(vdpfile)
            if data.scheme:
                r = requests.request("GET", vdpfile)
                vdpdata = r.text
            else:
                with open(vdpfile, "r") as f:
                    vdpdata = f.read(1000000000)
        if vdpdata or vdpfile:
            if type(vdpdata) is str:
                try:
                    vdpdata = json.loads(vdpdata)
                except Exception as e:
                    raise VDPException(str(e))
            try:
                VDPObject.validate(vdpdata, "Vdp", vdpfile)
                self._data = vdpdata
                if "file_type" in self._data and self._data["file_type"] == 'VPNDescriptionProtocol':
                    if "providers" in self._data:
                        for p in self._data["providers"]:
                            prov = Provider(p)
                            oldprov = self.get_provider(prov.get_id())
                            # Check if we have newer revision, otherwise do not update
                            if oldprov:
                                if oldprov.get_revision() <= prov.get_revision():
                                    self._providers[prov.get_id()] = prov
                                else:
                                    logging.getLogger("vdp").warning("Ignoring provider %s with lower revision" % prov.get_id())
                            else:
                                self._providers[prov.get_id()] = prov
                    if "spaces" in self._data:
                        for s in self._data["spaces"]:
                            spc = Space(s, vdp=self)
                            if not spc.get_provider_id() in self.provider_ids():
                                raise VDPException(
                                    "Providerid %s for space %s does not exists!" % (spc.get_provider_id(), spc))
                            oldspc = self.get_space(spc.get_id())
                            # Check if we have newer revision, otherwise do not update
                            if oldspc:
                                if oldspc.get_revision() <= spc.get_revision():
                                    self._spaces[spc.get_id()] = spc
                                else:
                                    logging.getLogger("vdp").warning("Ignoring Space %s with lower revision" % spc.get_id())
                            else:
                                self._spaces[spc.get_id()] = spc
                    if "gates" in self._data:
                        for g in self._data["gates"]:
                            gw = Gateway(g, vdp=self)
                            if not gw.get_provider_id() in self.provider_ids():
                                raise VDPException(
                                    "Providerid %s for gate %s does not exists!" % (gw.get_provider_id(), gw))
                            for s in gw.space_ids():
                                if s not in self.space_ids():
                                    raise VDPException("SpaceId %s for gate %s does not exists!" % (s, gw))
                            oldgw = self.get_gate(gw.get_id())
                            # Check if we have newer revision, otherwise do not update
                            if oldgw:
                                if oldgw.get_revision() <= gw.get_revision():
                                    self._gates[gw.get_id()] = gw
                                else:
                                    logging.getLogger("vdp").warning("Ignoring gate %s with lower revision" % gw.get_id())
                            else:
                                self._gates[gw.get_id()] = gw
                else:
                    if vdpfile:
                        logging.error("Bad VDP file %s" % vdpfile)
                    else:
                        logging.error("Bad VDP data %s" % vdpdata)
                    sys.exit(1)

            except Exception as e:
                raise VDPException(str(e))

        else:
            if my_only:
                providerfiles = glob.glob(Registry.cfg.my_providers_dir + "/*lprovider")
            else:
                providerfiles = glob.glob(Registry.cfg.providers_dir + "/*lprovider")
                providerfiles.extend(glob.glob(Registry.cfg.app_dir + "/config/providers/*lprovider"))
                providerfiles.extend(glob.glob(Registry.cfg.my_providers_dir + "/*lprovider"))
            for providerf in providerfiles:
                logging.getLogger().info("Loading provider %s" % providerf)
                with open(providerf, "r") as f:
                    jsn = f.read(-1)
                    try:
                        prov = Provider(json.loads(jsn), providerf)
                        if providerf.startswith(Registry.cfg.my_providers_dir):
                            prov.set_as_local()
                        oldprov = self.get_provider(prov.get_id())
                        # Check if we have newer revision, otherwise do not update
                        if oldprov:
                            if oldprov.get_revision() <= prov.get_revision():
                                self._providers[prov.get_id()] = prov
                            else:
                                logging.getLogger("vdp").warning(
                                    "Ignoring provider %s with lower revision" % prov.get_id())
                        else:
                            self._providers[prov.get_id()] = prov
                    except Exception as e:
                        print("Error loading %s: %s" % (providerf, e))

            if my_only:
                spacefiles = glob.glob(Registry.cfg.my_spaces_dir + "/*lspace")
            else:
                spacefiles = glob.glob(Registry.cfg.spaces_dir + "/*lspace")
                spacefiles.extend(glob.glob(Registry.cfg.app_dir + "/config/spaces/*lspace"))
                spacefiles.extend(glob.glob(Registry.cfg.my_spaces_dir + "/*lspace"))
            for spacef in spacefiles:
                logging.getLogger().info("Loading space %s" % spacef)
                with open(spacef, "r") as f:
                    jsn = f.read(-1)
                    try:
                        spc = Space(json.loads(jsn), spacef, vdp=self)
                        if not spc.get_provider_id() in self.provider_ids():
                            raise VDPException(
                                "Providerid %s for space %s does not exists!" % (spc.get_provider_id(), spc))
                        oldspc = self.get_space(spc.get_id())
                        # Check if we have newer revision, otherwise do not update
                        if oldspc:
                            if oldspc.get_revision() <= spc.get_revision():
                                self._spaces[spc.get_id()] = spc
                            else:
                                logging.getLogger("vdp").warning("Ignoring Space %s with lower revision" % spc.get_id())
                        else:
                            self._spaces[spc.get_id()] = spc
                    except Exception as e:
                        print("Error loading %s: %s" % (spacef, e))

            if my_only:
                gatefiles = glob.glob(Registry.cfg.my_gates_dir + "/*lgate")
            else:
                gatefiles = glob.glob(Registry.cfg.gates_dir + "/*lgate")
                gatefiles.extend(glob.glob(Registry.cfg.app_dir + "/config/gates/*lgate"))
                gatefiles.extend(glob.glob(Registry.cfg.my_gates_dir + "/*lgate"))
            for gwf in gatefiles:
                logging.getLogger().info("Loading gate %s" % gwf)
                with open(gwf, "r") as f:
                    jsn = f.read(-1)
                    try:
                        gw = Gateway(json.loads(jsn), gwf, vdp=self)
                        if not gw.get_provider_id() in self.provider_ids():
                            raise VDPException(
                                "Providerid %s for gate %s does not exists!" % (gw.get_provider_id(), gw))
                        for s in gw.space_ids():
                            if s not in self._spaces.keys():
                                raise VDPException("SpaceId %s for gate %s does not exists!" % (s, gw))
                        gw.set_provider(self._providers[gw.get_provider_id()])
                        oldgw = self.get_gate(gw.get_id())
                        # Check if we have newer revision, otherwise do not update
                        if oldgw:
                            if oldgw.get_revision() <= gw.get_revision():
                                self._gates[gw.get_id()] = gw
                            else:
                                logging.getLogger("vdp").warning("Ignoring gate %s with lower revision" % gw.get_id())
                        else:
                            self._gates[gw.get_id()] = gw
                    except Exception as e:
                        print("Error loading %s: %s" % (gwf, e))

        self._dict = {
            "file_type": "VPNDescriptionProtocol",
            "file_version": "1.1",
            "spaces": json.loads(self.spaces(as_json=True)),
            "gates": json.loads(self.gates(as_json=True)),
            "providers": json.loads(self.providers(as_json=True)),
            "signatures": []
        }
        self._json = json.dumps(self._dict, indent=2)
        self._localdict = {
            "file_type": "VPNDescriptionProtocol",
            "file_version": "1.1",
            "spaces": json.loads(self.spaces(my_only=True, as_json=True)),
            "gates": json.loads(self.gates(my_only=True, as_json=True)),
            "providers": json.loads(self.providers(my_only=True, as_json=True)),
            "signatures": []
        }
        self._localjson = json.dumps(self._localdict, indent=2)
        VDPObject.validate(self._dict, "Vdp")
        VDPObject.validate(self._localdict, "Vdp")
        logging.getLogger("vdp").warning(repr(self))

    def gates(self, filter: str = "", spaceid: str = None, my_only: bool = False, internal: bool = True, as_json: bool = False):
        """Return all gates"""
        gates = []
        for g in self._gates.values():
            if not internal and g.is_internal():
                continue
            if my_only and not g.is_local():
                continue
            if (filter == "") or g.get_json().find(filter) >= 0:
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

    def spaces(self, filter: str = "", my_only: bool = False, as_json: bool = False):
        spaces = []
        for s in self._spaces.values():
            if my_only and not s.is_local():
                continue
            if (filter == "") or s.get_json().find(filter) >= 0:
                if as_json:
                    spaces.append(s.get_dict())
                else:
                    spaces.append(s)
        if as_json:
            return json.dumps(spaces)
        else:
            return spaces

    def providers(self, filter: str = "", my_only: bool = False, as_json: bool = False):
        providers = []
        for s in self._providers.values():
            if my_only and not s.is_local():
                continue
            if (filter == "") or s.get_json().find(filter) >= 0:
                if as_json:
                    providers.append(s.get_dict())
                else:
                    providers.append(s)
        if as_json:
            return json.dumps(providers)
        else:
            return providers

    def get_json(self, my_only: bool = False):
        if my_only:
            return self._localjson
        else:
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
            Registry.cfg = cfg
        saved_gates = 0
        saved_spaces = 0
        saved_providers = 0
        ignored_gates = 0
        ignored_spaces = 0
        ignored_providers = 0
        for g in self.gate_ids():
            go = self.get_gate(g)
            if go.get_provider().get_id() in Registry.cfg.readonly_providers:
                logging.getLogger("vdp").info("Not saving gate %s (Readonly provider)" % go.get_id())
                ignored_gates += 1
                continue
            saved_gates += 1
            go.save(cfg=cfg)
        for s in self.space_ids():
            so = self.get_space(s)
            if so.get_provider().get_id() in Registry.cfg.readonly_providers:
                logging.getLogger("vdp").info("Not saving space %s (Readonly provider)" % so.get_id())
                ignored_spaces += 1
                continue
            saved_spaces += 1
            so.save(cfg=cfg)
        for p in self.provider_ids():
            if p in Registry.cfg.readonly_providers:
                logging.getLogger("vdp").info("Not saving provider %s (Readonly provider)" % p)
                ignored_providers += 1
                continue
            po = self.get_provider(p)
            saved_providers += 1
            po.save(cfg=cfg)
        return {
            "saved_spaces": saved_spaces,
            "saved_providers": saved_providers,
            "saved_gates": saved_gates,
            "ignored_spaces": ignored_spaces,
            "ignored_providers": ignored_providers,
            "ignored_gates": ignored_gates,
        }

    def __repr__(self):
        return "VDP[providers=%s,spaces=%s,gates=%s,local_providers=%s]" % (len(self._providers), len(self._spaces), len(self._gates), len(self.providers(my_only=True)))
