import json
import time
import secrets


class Session:

    def __init__(self, cfg, data=None):
        self._cfg = cfg
        self._data = data

    def generate(self, gateid, spaceid, days):
        self._data = {
            "sessionid": secrets.token_hex(8),
            "space": self._cfg.vdp.get_space(spaceid),
            "gate": self._cfg.vdp.get_gate(gateid),
            "created": int(time.time()),
            "paymentid": secrets.token_hex(8),
            "username": "user_" + secrets.token_hex(5),
            "password": secrets.token_hex(10),
            "bearer": secrets.token_hex(12),
            "wallet": self._cfg.vdp.get_space(spaceid).get_wallet(),
            "days": int(days),
            "price":  (self._cfg.vdp.get_space(spaceid) + self._cfg.vdp.get_gate(gateid)) * days
        }

    def get_id(self):
        return self.data["sessionid"]

    def get_paymentid(self):
        return self.data["paymentid"]

    def save(self, file=None):
        if not file:
            file = "%s/%s.lsession" % (self._cfg.sessions_dir, self.get_id())
        with open(file, "w") as f:
            f.write(json.dumps(self._data))

    def load(self, file):
        with open(file, "r") as f:
            buf = f.read(10000)
            self._data = json.loads(buf)

    def is_for_gate(self, gateid):
        return self._data["gate"].get_id() == gateid

    def is_for_space(self, spaceid):
        return self._data["space"].get_id() == spaceid

    def days_left(self):
        seconds = (self._data["created"] + (self._data["days"] * 3600 * 24)) - time.time()
        return int(seconds/3600/24)

    def is_fresh(self):
        return self.days_left() < 0

    def __str__(self):
        return json.dumps(self._data)

    def __repr__(self):
        try:
            txt = "Session[%s(days=%s)]" % (self.get_id(), self._data["days"])
        except Exception as e:
            txt = "Session[Empty]"
        return txt
