import time
import secrets


class AuthID:

    def __init__(self, time=None, days=None, gateid=None, spaceid=None, authid=None):
        self._gateid = gateid
        self._spaceid = spaceid
        if not authid:
            authid = self.generate(days)
        self._authid = authid
        if not time:
            time = time.time()
        self._time = time
        self._days = days

    def generate(self, days):
        self._days = days
        return secrets.token_hex(8)

    def get_id(self):
        return self._authid

    def save(self, file):
        with  open(file, "w") as f:
            f.write("%s/%s/%s/%s/%s" % (time.time(), self._days, self._spaceid, self._gateid, self._authid))

    def load(self, file):
        with open(file, "r") as f:
            buf = f.read(10000)
            (self._time, self._days, self._spaceid, self._gateid, self._authid) = buf.split("/")

    def is_for_gate(self, gateid):
        return self._gateid == gateid

    def is_for_space(self, spaceid):
        return self._spaceid == spaceid

    def days_left(self):
        seconds = (self._time + (self._days * 3600 * 24)) - time.time()
        return int(seconds/3600/24)

    def is_fresh(self):
        return self.days_left() < 0

    def __str__(self):
        return self._authid
