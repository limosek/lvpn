import json
import tempfile
import os


class VDPObject:

    def get_name(self):
        return self._data["name"]

    def get_type(self):
        return self._data["type"]

    def get_manager_url(self):
        return "https://%s:%s" % (self._data["manager"]["host"], self._data["manager"]["port"])

    def get_price(self):
        if "price" in self._data and "per-day" in self._data["price"]:
            return self._data["price"]["per-day"]
        else:
            return 0

    def get_wallet(self):
        return self._data["wallet"]

    def get_json(self):
        return json.dumps(self._data, indent=2)

    def get_dict(self):
        return self._data

    def get_ca(self):
        return "-----BEGIN CERTIFICATE-----\n%s\n-----END CERTIFICATE-----\n" % self._data["ca"]

    def get_cafile(self, tmpdir):
        (fd, path) = tempfile.mkstemp(dir=tmpdir, prefix="ca", suffix=".crt", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(self.get_ca())
        return path

    def toJson(self):
        return self.get_json()
