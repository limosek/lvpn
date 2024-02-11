import json
import logging
import time
import secrets
from copy import copy

from lib.shared import Messages
from lib.vdpobject import VDPException


class Session:

    def __init__(self, cfg, data=None):
        self._cfg = cfg
        self._data = data
        if data:
            if "gateid" in data:
                self._gate = self._cfg.vdp.get_gate(data["gateid"])
            if "spaceid" in data:
                self._space = self._cfg.vdp.get_space(data["spaceid"])

    def generate(self, gateid, spaceid, days):
        if not self._cfg.vdp.get_space(spaceid):
            raise VDPException("Unknown space %s" % spaceid)
        if not self._cfg.vdp.get_gate(gateid):
            raise VDPException("Unknown gate %s" % gateid)
        price = (self._cfg.vdp.get_space(spaceid).get_price() + self._cfg.vdp.get_gate(gateid).get_price()) * days
        self._data = {
            "sessionid": "s-" + secrets.token_hex(8),
            "spaceid": spaceid,
            "gateid": gateid,
            "created": int(time.time()),
            "paymentid": secrets.token_hex(8),
            "username": "u-" + secrets.token_hex(5),
            "password": secrets.token_hex(10),
            "bearer": "b-" + secrets.token_hex(12),
            "wallet": self._cfg.vdp.get_space(spaceid).get_wallet(),
            "days": int(days),
            "expires": int(time.time()) + self._cfg.unpaid_expiry,
            "paid": price == 0,
            "payments": [],
            "activated": 0,
            "price": price,
            "payment_sent": False
        }
        self._gate = self._cfg.vdp.get_gate(gateid)
        self._space = self._cfg.vdp.get_space(spaceid)
        if self.get_price() == 0:
            self.activate()

    def activate(self):
        now = int(time.time())
        self._data["expires"] = now + self._data["days"] * 3600 * 24
        self._data["activated"] = now
        logging.getLogger().warning("Activated session %s" % self.get_id())

    def get_spaceid(self):
        return self._space.get_id()

    def get_gateid(self):
        return self._gate.get_id()

    def get_space(self):
        return self._space

    def get_gate(self):
        return self._gate

    def get_manager_url(self):
        return self._space.get_manager_url()

    def get_id(self):
        return self._data["sessionid"]

    def get_price(self):
        return self._data["price"]

    def get_payment(self):
        paid = 0
        for p in self._data["payments"]:
            paid += p["amount"]
        return paid

    def get_activation(self):
        return self._data["activated"]

    def add_payment(self, amount, height, txid):
        payment = {"amount": amount, "height": height, "txid": txid}
        if payment not in self._data["payments"]:
            self._data["payments"].append(payment)
            if self.get_payment() >= self._data["price"]:
                self._data["paid"] = True
                self.activate()
            else:
                self._data["paid"] = False
            return True
        else:
            return False

    def set_parent(self, parentid):
        self._data["parent"] = parentid

    def get_parent(self):
        if "parent" in self._data:
            return self._data["parent"]
        else:
            return False

    def is_paid(self):
        return self._data["paid"]

    def is_free(self):
        return self.get_price() == 0

    def is_active(self):
        return self._data["activated"] != 0

    def is_payment_sent(self):
        if "payment_sent" in self._data:
            return self._data["payment_sent"]
        else:
            return False

    def payment_sent(self, msg):
        self._data["payment_sent"] = msg

    def get_paymentid(self):
        return self._data["paymentid"]

    def get_filename(self):
        return "%s/%s.lsession" % (self._cfg.sessions_dir, self.get_id())

    def save(self, file=None):
        if not file:
            file = self.get_filename()
        with open(file, "w") as f:
            f.write(json.dumps(self._data))

    def load(self, file):
        with open(file, "r") as f:
            buf = f.read(10000)
            self._data = json.loads(buf)
        self._gate = self._cfg.vdp.get_gate(self._data["gateid"])
        self._space = self._cfg.vdp.get_space(self._data["spaceid"])

    def is_for_gate(self, gateid):
        return self._gate.get_id() == gateid

    def is_for_space(self, spaceid):
        return self._space.get_id() == spaceid

    def days_left(self):
        seconds = (self._data["expires"] - time.time())
        return int(seconds/3600/24)

    def seconds_left(self):
        seconds = (self._data["expires"] - time.time())
        return int(seconds)

    def is_fresh(self):
        return self._data["expires"] > time.time()

    def get_dict(self):
        data = copy(self._data)
        if "payment_sent" in data:
            del data["payment_sent"]
        return data

    def get_pay_msg(self):
        m = Messages.pay([{
            "wallet": self._data["wallet"],
            "amount": self._data["price"]
        }], self.get_paymentid())
        return m

    def __str__(self):
        return json.dumps(self._data)

    def get_title(self):
        txt = "%s/%s" % (self.get_gate(), self.get_space())
        return txt

    def __repr__(self):
        try:
            txt = "Session-%s[%s/%s,days=%s,price=%s,payments=%s,paid=%s,fresh=%s]" % (self.get_gate(), self.get_space(), self._data["days"], self.get_id(), self.get_price(), self.get_payment(), self.is_paid(), self.is_fresh())
        except Exception as e:
            txt = "Session[Empty]"
        return txt
