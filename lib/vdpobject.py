import json
import tempfile
import os


class VDPException(Exception):
    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)

    def __str__(self):
        return "%s: %s" % (self.__class__, self.message)


class VDPObject:

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

    def is_internal(self):
        if "internal" in self._data:
            if self._data["internal"]:
                return True
        return False

    def toJson(self):
        return self.get_json()

    def __getitem__(self, item):
        if item in self._data:
            return self._data[item]
        else:
            return None
