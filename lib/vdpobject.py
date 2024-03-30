import json
import logging
import sqlite3
import tempfile
import os
import time

import jsonschema
import openapi_schema_validator
from jsonschema.exceptions import ValidationError
from openapi_core import OpenAPI

from lib.db import DB
from lib.registry import Registry


class VDPException(Exception):
    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)

    def __str__(self):
        return "%s: %s" % (self.__class__, self.message)


class VDPObject:
    cfg = False
    tpe = None

    @classmethod
    def validate(cls, data, schema=None, file=None):
        if not schema:
            schema = cls.tpe
        openapi = OpenAPI.from_file_path(os.path.dirname(__file__) + "/../misc/schemas/server.yaml")
        spc = openapi.spec.contents()
        resolver = jsonschema.validators.RefResolver.from_schema(spc)
        validator = openapi_schema_validator.OAS31Validator(spc["components"]["schemas"][schema],
                                                            resolver=resolver)
        try:
            validator.validate(data)
        except ValidationError as e:
            raise VDPException("Bad schema: %s/%s/%s" % (file, schema, e.message))

    def is_local(self):
        return self._local

    def set_as_local(self):
        self._local = True

    def is_fresh(self):
        if "revision" and "ttl" in self._data:
            # If revision + TTL is bigger than now, we are fresh
            return self._data["revision"] + self._data["ttl"] > int(time.time())
        else:
            # We have no info, assuming fresh
            return True

    def set_as_fresh(self):
        self._data["revision"] = int(time.time())

    def get_name(self):
        return self._data["name"]

    def set_name(self, name):
        self._data["name"] = name

    def get_type(self):
        return self._data["type"]

    def get_provider_id(self):
        return self._data["providerid"]

    def get_provider(self):
        return self._provider

    def get_manager_url(self):
        if Registry.cfg and Registry.cfg.force_manager_url:
            logging.getLogger("vdp").warning("Using forced manager URL %s" % Registry.cfg.force_manager_url)
            return Registry.cfg.force_manager_url
        else:
            if "manager-url" in self._data:
                return self._data["manager-url"]
            else:
                return self.get_provider().get_manager_url()

    def get_price(self):
        if "price" in self._data and "per-day" in self._data["price"]:
            return self._data["price"]["per-day"]
        else:
            return 0

    def get_json(self):
        return json.dumps(self._data, indent=2)

    def get_dict(self):
        return self._data

    def get_cafile(self, tmpdir):
        (fd, path) = tempfile.mkstemp(dir=tmpdir, prefix="ca", suffix=".crt", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(self.get_ca())
        return path

    def get_keyfile(self, tmpdir, key):
        (fd, path) = tempfile.mkstemp(dir=tmpdir, prefix=key, suffix=".key", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(self[self.get_type()][key])
        return path

    def get_revision(self):
        if "revision" in self._data:
            return self._data["revision"]
        else:
            return 0

    def get_ttl(self):
        if "ttl" in self._data:
            return self._data["ttl"]
        else:
            return 3600*24*30

    def get_expiry(self):
        if self.get_revision() and self.get_ttl():
            return self.get_revision() + self.get_ttl()
        else:
            return int(time.time() + 3600*24*30)

    def is_internal(self):
        if "internal" in self._data:
            if self._data["internal"]:
                return True
        return False

    def toJson(self):
        return self.get_json()

    def save(self):
        db = DB()
        if self.get_revision() > 0:
            sql = "SELECT COUNT(*) FROM vdp WHERE tpe='{tpe}' and id='{id}' AND revision>{revision}".format(
                tpe=self.tpe,
                id=self.get_id(),
                revision=self.get_revision()
            )
            cnt = db.select(sql)[0][0]
        else:
            cnt = 0
        if cnt == 0:
            db.begin()
            sql = "DELETE FROM vdp WHERE tpe='{tpe}' and id='{id}'".format(
                tpe=self.tpe,
                id=self.get_id()
            )
            db.execute(sql)
            sql = """
                INSERT INTO vdp
                  (id, tpe, data, deleted, my, readonly, expiry, revision, ttl)
                  VALUES ('{id}', '{tpe}', '{data}', False, {my}, {ro}, {expiry}, {revision}, {ttl})
                """.format(
                    tpe=self.tpe,
                    id=self.get_id(),
                    data=json.dumps(self.get_dict()),
                    my=self.is_local(),
                    ro=self.get_provider_id() in Registry.cfg.readonly_providers,
                    expiry=self.get_expiry(),
                    revision=self.get_revision(),
                    ttl=self.get_ttl()
                )
            db.execute(sql)
            db.commit()
        else:
            sql = "SELECT id,revision FROM vdp WHERE tpe='{tpe}' and id='{id}' AND revision>{revision}".format(
                tpe=self.tpe,
                id=self.get_id(),
                revision=self.get_revision()
            )
            fresh = db.select(sql)
            logging.getLogger("vdp").warning("Not saving vdp object %s/revision=%s because we have fresher object in DB (revision=%s)" % (self.get_id(), self.get_revision(), fresh[0][0]))
        db.close()
        pass

    def __getitem__(self, item):
        if item in self._data:
            return self._data[item]
        else:
            return None
