import json
import logging
import sys
import time
import cachetools.func
import requests
import urllib3

from lib.db import DB
from lib.registry import Registry
from lib.space import Space
from lib.provider import Provider
from lib.vdpobject import VDPException, VDPObject
import lib.gate


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
            VDPObject.validate(vdpdata, "Vdp", vdpfile)
            self._data = vdpdata
            if "file_type" in self._data and self._data["file_type"] == 'VPNDescriptionProtocol':
                if "providers" in self._data:
                    for p in self._data["providers"]:
                        prov = Provider(p)
                        prov.save()
                if "spaces" in self._data:
                    for s in self._data["spaces"]:
                        spc = Space(s, vdp=self)
                        if not spc.get_provider_id() in self.provider_ids():
                            raise VDPException(
                                "Providerid %s for space %s does not exists!" % (spc.get_provider_id(), spc))
                        spc.save()
                if "gates" in self._data:
                    for g in self._data["gates"]:
                        gw = lib.Gateway(g, vdp=self)
                        if not gw.get_provider_id() in self.provider_ids():
                            raise VDPException(
                                "Providerid %s for gate %s does not exists!" % (gw.get_provider_id(), gw))
                        for s in gw.space_ids():
                            if s not in self.space_ids():
                                raise VDPException("SpaceId %s for gate %s does not exists!" % (s, gw))
                        gw.save()
            else:
                if vdpfile:
                    logging.error("Bad VDP file %s" % vdpfile)
                else:
                    logging.error("Bad VDP data %s" % vdpdata)
                sys.exit(1)

    def objects(self, tpe, only_id, filter: str = "", spaceid: str = None, my_only: bool = False, internal: bool = True, fresh: bool = True, as_json: bool = False, deleted=False):
        db = DB()
        ands = []
        if filter:
            ands.append("data LIKE %%%s%%" % filter)
        if my_only:
            ands.append("my IS TRUE")
        if fresh:
            ands.append("expiry > %s" % time.time())
        if only_id:
            attr = "id"
        else:
            attr = "data"
        if spaceid:
            ands.append("data LIKE '%%\"spaces\": [%%%s%%]%%' " % spaceid)
        if not internal:
            ands.append(" NOT " + db.cmp_bool_attr("internal"))
        if not deleted:
            ands.append("deleted IS FALSE")
        srows = db.select("SELECT %s,my from vdp WHERE tpe='%s' %s" % (attr, tpe, db.parse_ands(ands)))
        db.close()
        rows = []
        if Registry.cfg.is_server:
            if Registry.cfg.provider_id:
                providerid = Registry.cfg.provider_id
            else:
                try:
                    with open(Registry.cfg.provider_public_key, "r") as pf:
                        providerid = pf.read(-1).strip()
                except FileNotFoundError:
                    providerid = "none"
        else:
            providerid = "none"
        for r in srows:
            if only_id:
                rows.append(r[0])
            elif as_json:
                rows.append(json.loads(r[0]))
            else:
                if tpe == "Provider":
                    s = Provider(json.loads(r[0]))
                    if r[1] or s.get_id() == providerid:
                        s.set_as_local()
                elif tpe == "Space":
                    s = Space(json.loads(r[0]))
                    if r[1] or s.get_id() == providerid:
                        s.set_as_local()
                elif tpe == "Gate":
                    s = lib.Gateway(json.loads(r[0]))
                    if r[1] or s.get_id() == providerid:
                        s.set_as_local()
                else:
                    raise VDPException("Bad object type %s" % tpe)
                rows.append(s)
        if as_json:
            return json.dumps(rows)
        else:
            return rows

    @cachetools.func.ttl_cache(ttl=60)
    def gates(self, filter: str = "", spaceid: str = None, my_only: bool = False, internal: bool = True, fresh: bool = True, as_json: bool = False, deleted: bool = False):
        """Return all gates"""
        return self.objects('Gate', False, filter=filter, spaceid=spaceid, my_only=my_only, internal=internal, fresh=fresh, as_json=as_json, deleted=deleted)

    @cachetools.func.ttl_cache(ttl=60)
    def spaces(self, filter: str = "", my_only: bool = False, fresh: bool = True, as_json: bool = False, deleted: bool = False):
        return self.objects('Space', False, filter=filter, my_only=my_only, fresh=fresh, as_json=as_json, deleted=deleted)

    @cachetools.func.ttl_cache(ttl=60)
    def providers(self, filter: str = "", my_only: bool = False, fresh: bool = True, as_json: bool = False, deleted: bool = False):
        return self.objects('Provider', False, filter=filter, my_only=my_only, fresh=fresh, as_json=as_json, deleted=deleted)

    def get_json(self, my_only: bool = False):
        return json.dumps(self.get_dict(my_only), indent=2)

    def get_dict(self, my_only=False):
        objects = self.providers(fresh=False)
        objects.extend(self.spaces(fresh=False))
        objects.extend(self.gates(fresh=False))

        d = {
            "file_type": "VPNDescriptionProtocol",
            "file_version": "1.1",
            "spaces": json.loads(self.spaces(as_json=True, my_only=my_only)),
            "gates": json.loads(self.gates(as_json=True, my_only=my_only)),
            "providers": json.loads(self.providers(as_json=True, my_only=my_only)),
            "signatures": []
        }
        VDPObject.validate(d, "Vdp")
        return d

    @cachetools.func.ttl_cache(ttl=60)
    def gate_ids(self):
        return self.objects('Gate', True)

    @cachetools.func.ttl_cache(ttl=60)
    def space_ids(self):
        return self.objects('Space', True)

    @cachetools.func.ttl_cache(ttl=60)
    def provider_ids(self):
        return self.objects('Provider', True)

    @cachetools.func.ttl_cache(ttl=60)
    def get_gate(self, gwid):
        db = DB()
        p = db.select("SELECT data,my FROM vdp WHERE tpe='Gate' AND id='%s' AND deleted IS FALSE" % gwid)
        db.close()
        if len(p) > 0:
            data = lib.Gateway(json.loads(p[0][0]))
            if p[0][1] or data.get_provider_id() == Registry.cfg.provider_id:
                data.set_as_local()
            return data
        else:
            return None

    @cachetools.func.ttl_cache(ttl=60)
    def get_space(self, spaceid):
        db = DB()
        p = db.select("SELECT data,my FROM vdp WHERE tpe='Space' AND id='%s' AND deleted IS FALSE" % spaceid)
        db.close()
        if len(p) > 0:
            data = Space(json.loads(p[0][0]))
            if p[0][1] or data.get_provider_id() == Registry.cfg.provider_id:
                data.set_as_local()
            return data
        else:
            db.close()
            return None

    @cachetools.func.ttl_cache(ttl=60)
    def get_provider(self, providerid):
        db = DB()
        p = db.select("SELECT data,my FROM vdp WHERE tpe='Provider' AND id='%s' AND deleted IS FALSE" % providerid)
        db.close()
        if len(p) > 0:
            data = Provider(json.loads(p[0][0]))
            if p[0][1] or data.get_id() == Registry.cfg.provider_id:
                data.set_as_local()
            return data
        else:
            return None

    @classmethod
    def load_file(cls, file, vdp):
        with open(file, "r") as f:
            jsn = json.loads(f.read(-1))
            if file.endswith(".lprovider"):
                return Provider(jsn, file)
            elif file.endswith(".lspace"):
                return Space(jsn, file, vdp)
            elif file.endswith(".lgate"):
                return lib.Gateway(jsn, file, vdp)
            else:
                raise VDPException("Unknown file type %s" % file)

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
                logging.getLogger("vdp").debug("Not saving gate %s (Readonly provider)" % go.get_id())
                ignored_gates += 1
                continue
            saved_gates += 1
            go.save()
        for s in self.space_ids():
            so = self.get_space(s)
            if so.get_provider().get_id() in Registry.cfg.readonly_providers:
                logging.getLogger("vdp").debug("Not saving space %s (Readonly provider)" % so.get_id())
                ignored_spaces += 1
                continue
            saved_spaces += 1
            so.save()
        for p in self.provider_ids():
            if p in Registry.cfg.readonly_providers:
                logging.getLogger("vdp").debug("Not saving provider %s (Readonly provider)" % p)
                ignored_providers += 1
                continue
            po = self.get_provider(p)
            saved_providers += 1
            po.save()
        return {
            "saved_spaces": saved_spaces,
            "saved_providers": saved_providers,
            "saved_gates": saved_gates,
            "ignored_spaces": ignored_spaces,
            "ignored_providers": ignored_providers,
            "ignored_gates": ignored_gates,
        }

    def __repr__(self):
        return "VDP[providers=%s,spaces=%s,gates=%s,local_providers=%s,fresh_providers=%s]" % (len(self.providers()), len(self.spaces()), len(self.gates()), len(self.providers(my_only=True)), len(self.providers(fresh=True)))
