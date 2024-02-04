import json
import time
import secrets


class Session:

    def __init__(self, cfg, data=None):
        self._cfg = cfg
        self._data = data
        if data:
            if "gateid" in data:
                self._gate = self._cfg.vdp.get_gate(data["gateid"])
            if "spaceid" in data:
                self._space = self._cfg.vdp.get_gate(data["spaceid"])

    def generate(self, gateid, spaceid, days):
        price = (self._cfg.vdp.get_space(spaceid).get_price() + self._cfg.vdp.get_gate(gateid).get_price()) * days
        self._data = {
            "sessionid": secrets.token_hex(8),
            "spaceid": spaceid,
            "gateid": gateid,
            "created": int(time.time()),
            "paymentid": secrets.token_hex(8),
            "username": "user_" + secrets.token_hex(5),
            "password": secrets.token_hex(10),
            "bearer": secrets.token_hex(12),
            "wallet": self._cfg.vdp.get_space(spaceid).get_wallet(),
            "days": int(days),
            "expires": int(time.time()) + int(days)*3600*24,
            "paid": price == 0,
            "price": price
        }
        self._gate = self._cfg.vdp.get_gate(gateid)
        self._space = self._cfg.vdp.get_space(spaceid)

    def get_spaceid(self):
        return self._space.get_id()

    def get_gateid(self):
        return self._gate.get_id()

    def get_id(self):
        return self._data["sessionid"]

    def get_price(self):
        return self._data["price"]

    def is_paid(self):
        return self._data["paid"]

    def get_paymentid(self):
        return self._data["paymentid"]

    def save(self, file=None):
        if not file:
            file = "%s/%s.lsession" % (self._cfg.sessions_dir, self.get_id())
        with open(file, "w") as f:
            f.write(json.dumps(self._data))

    def load(self, file):
        with open(file, "r") as f:
            buf = f.read(10000)
            self._data = json.loads(buf)
        self._gate = self._cfg.vdp.get_gate(self._data["gateid"])
        self._space = self._cfg.vdp.get_gate(self._data["spaceid"])

    def is_for_gate(self, gateid):
        return self._gate.get_id() == gateid

    def is_for_space(self, spaceid):
        return self._space.get_id() == spaceid

    def days_left(self):
        seconds = (self._data["created"] + (self._data["days"] * 3600 * 24)) - time.time()
        return int(seconds/3600/24)

    def is_fresh(self):
        return self.days_left() > 0

    def get_dict(self):
        return self._data

    def __str__(self):
        return json.dumps(self._data)

    def __repr__(self):
        try:
            txt = "Session[%s(days=%s)]" % (self.get_id(), self._data["days"])
        except Exception as e:
            txt = "Session[Empty]"
        return txt
