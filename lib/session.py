import json
import logging
import time
import secrets
from copy import copy

from lib.registry import Registry
from lib.runcmd import RunCmd
from lib.vdpobject import VDPException, VDPObject
import lib


class Session:

    def __init__(self, data=None):
        self._data = data
        self._contributions_price = 0
        if data:
            if "gateid" in data:
                self._gate = Registry.vdp.get_gate(data["gateid"])
            if "spaceid" in data:
                self._space = Registry.vdp.get_space(data["spaceid"])
            if not self._gate:
                raise VDPException("Gate %s for session %s unknown!" % (data["gateid"], self.get_id()))
            if not self._space:
                raise VDPException("Space %s for session %s unknown!" % (data["spaceid"], self.get_id()))
            if self.is_free() \
                    and self._gate.get_type() == "wg" \
                    and self.get_gate_data("wg") \
                    and not self.is_active():
                self.activate()
            else:
                if "contributions" not in self._data:
                    self._data["contributions"] = []
                self.recalculate_contributions(True)

    def generate(self, gateid: str, spaceid: str, days: int = None):
        if not Registry.vdp.get_space(spaceid):
            raise VDPException("Unknown space %s" % spaceid)
        if not Registry.vdp.get_gate(gateid):
            raise VDPException("Unknown gate %s" % gateid)
        self._gate = Registry.vdp.get_gate(gateid)
        self._space = Registry.vdp.get_space(spaceid)
        self._contributions_price = 0
        self._data = {
            "sessionid": "s-" + secrets.token_hex(32),
            "spaceid": spaceid,
            "gateid": gateid,
            "created": int(time.time()),
            "paymentid": secrets.token_hex(8),
            "username": "u-" + secrets.token_hex(8),
            "password": secrets.token_hex(16),
            "bearer": "b-" + secrets.token_hex(32),
            "wallet": Registry.vdp.get_space(spaceid).get_wallet(),
            "expires": int(time.time()) + Registry.cfg.unpaid_expiry,
            "paid": False,
            "payments": [],
            "contributions": [],
            "activated": 0,
            "payment_sent": ""
        }

        if self.is_free():
            if not days:
                self._data["days"] = Registry.cfg.free_session_days
            else:
                self._data["days"] = days
            self._data["price"] = 0
            if self._gate.get_type() not in ["wg"]:
                self.activate()
            self.payment_sent("Zero-Free-payment")
        else:
            if not days:
                self._data["days"] = Registry.cfg.default_pay_days
            else:
                self._data["days"] = int(days)
            self._data["price"] = (
                                    Registry.vdp.get_space(spaceid).get_price()
                                    + Registry.vdp.get_gate(gateid).get_price()) * self._data["days"]
            if Registry.cfg.is_client:
                """Clients contributes by adding price"""
                self.recalculate_contributions(increase=True)
            elif Registry.cfg.is_server:
                """Server contributes by decreasing price"""
                self.recalculate_contributions(increase=False)

    def recalculate_contributions(self, increase=False):
        """Recalculate price by contributions. If increase is True, contributions are added to price, if False,
        price is decreased by contributions"""
        if Registry.cfg.contributions and not self.is_free():
            try:
                carr = []
                contributions = Registry.cfg.contributions.split(",")
                for s in contributions:
                    (swallet, purpose, amount) = s.split("/")
                    if amount.find("%") > 0:
                        amount = self.get_price() * (float(amount[:-1])/100)
                    else:
                        amount = float(amount)
                    carr.append({"wallet": swallet, "purpose": purpose, "price": amount})
                    self._contributions_price += amount
                if increase:
                    self._data["price"] += self._contributions_price
                else:
                    self._data["price"] -= self._contributions_price
            except Exception as e:
                logging.getLogger("audit").error("Bad contributions setting %s, but continuing" % Registry.cfg.contributions)
        for c in self._data["contributions"]:
            self._contributions_price += c["price"]

    def get_contributions_info(self):
        info = ""
        for c in self._data["contributions"]:
            info += "  price: %s, purpose: %s, wallet: %s" % (c["price"], c["purpose"], c["wallet"])
        return info

    def reuse(self, days):
        price = (self._space.get_price() + self._gate.get_price()) * days
        self._data["sessionid"] = "s-" + secrets.token_hex(8)
        self._data["wallet"] = self._space.get_wallet()
        self._data["created"] = int(time.time())
        self._data["paymentid"] = secrets.token_hex(8)
        self._data["password"] = secrets.token_hex(10)
        self._data["bearer"] = "b-" + secrets.token_hex(12)
        self._data["days"] = int(days)
        self._data["expires"] = int(time.time()) + Registry.cfg.unpaid_expiry
        self._data["paid"] = False
        self._data["payments"] = []
        self._data["activated"] = 0
        self._data["price"] = price,
        self._data["payment_sent"] = ""
        self.recalculate_contributions(increase=False)

    def activate(self):
        if self.get_payment() >= self._data["price"] and not self.is_active():
            logging.getLogger("audit").debug("Trying to activate session %s" % self.get_id())
            now = int(time.time())
            if Registry.cfg.is_server:
                self._gate.activate_server(self)
                self._space.activate_server(self)
            elif Registry.cfg.is_client:
                self._gate.activate_client(self)
                self._space.activate_client(self)
            if Registry.cfg.on_session_activation:
                RunCmd.run("%s %s" % (Registry.cfg.on_session_activation, self.get_filename()))
            logging.getLogger().warning("Activated session %s[free=%s]" % (self.get_id(), self.is_free()))
            self._data["expires"] = now + self._data["days"] * 3600 * 24
            self._data["activated"] = now
            logging.getLogger("audit").warning("Activated session %s" % self.get_id())
            return True
        else:
            return False

    def deactivate(self):
        if self.is_active():
            try:
                logging.getLogger("audit").debug("Trying to deactivate session %s" % self.get_id())
                if Registry.cfg.is_server:
                    self._gate.deactivate_server(self)
                    self._space.deactivate_server(self)
                elif Registry.cfg.is_client:
                    self._gate.deactivate_client(self)
                    self._space.deactivate_client(self)
                if Registry.cfg.on_session_deactivation:
                    RunCmd.run("%s %s" % (Registry.cfg.on_session_deactivation, self.get_filename()))
                logging.getLogger("audit").warning("Deactivated session %s[free=%s]" % (self.get_id(), self.is_free()))
                return True
            except Exception as e:
                logging.getLogger("audit").warning("Error deactivating session %s:%s" % (self.get_id(), e))
                raise
        else:
            return False

    def get_spaceid(self):
        return self._space.get_id()

    def get_gateid(self):
        return self._gate.get_id()

    def get_space(self):
        return self._space

    def get_gate(self):
        return self._gate

    def get_created(self):
        return self._data["created"]

    def get_manager_url(self):
        return self._space.get_manager_url()

    def get_id(self):
        return self._data["sessionid"]

    def get_price(self):
        return self._data["price"]

    def get_contributions_price(self):
        return self._contributions_price

    def get_expiry(self):
        return self._data["expires"]

    def get_payment(self):
        paid = 0
        for p in self._data["payments"]:
            paid += p["amount"]
        return paid

    def get_activation(self):
        return self._data["activated"]

    def add_payment(self, amount, height, txid):
        payment = {"amount": amount, "height": height, "txid": txid}
        for p in self._data["payments"]:
            if p["height"] == height and p["txid"] == txid:
                logging.getLogger().debug(
                    "Ignoring payment to session %s (already processed,paid:%s)" % (self.get_id(), self.get_payment()))
                return False
        logging.getLogger("audit").info("Adding new payment to session %s (paid:%s)" % (self.get_id(), self.get_payment()))
        self._data["payments"].append(payment)
        if self.get_payment() >= self._data["price"]:
            self._data["paid"] = True
            self.activate()
        else:
            self._data["paid"] = False
        self.save()
        return True

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
        return (self._space.get_price() + self._gate.get_price()) == 0

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
        return "%s/%s.lsession" % (Registry.cfg.sessions_dir, self.get_id())

    def save(self, file=None):
        if not file:
            file = self.get_filename()
        with open(file, "w") as f:
            logging.getLogger("audit").debug("Saving session %s" % self.get_id())
            f.write(json.dumps(self._data))

    def load(self, file):
        #logging.getLogger("audit").debug("Trying to load session from file %s" % file)
        with open(file, "r") as f:
            buf = f.read(-1)
            self._data = json.loads(buf)
            #logging.getLogger("audit").debug("Loaded session %s from file %s" % (self.get_id(), file))
        self._gate = Registry.vdp.get_gate(self._data["gateid"])
        self._space = Registry.vdp.get_space(self._data["spaceid"])
        if not self._gate:
            raise VDPException("Gate %s for session %s unknown!" % (self._data["gateid"], self.get_id()))
        if not self._space:
            raise VDPException("Space %s for session %s unknown!" % (self._data["spaceid"], self.get_id()))

    def is_for_gate(self, gateid):
        return self._gate.get_id() == gateid

    def is_for_space(self, spaceid):
        return self._space.get_id() == spaceid

    def days(self):
        return self._data["days"]

    def days_left(self):
        seconds = (self._data["expires"] - time.time())
        return int(seconds/3600/24)

    def hours_left(self):
        seconds = (self._data["expires"] - time.time())
        return int(seconds/3600)

    def seconds_left(self):
        seconds = (self._data["expires"] - time.time())
        return int(seconds)

    def pay_info(self):
        if self.get_gate().is_internal():
            return "Internal"
        else:
            if self.is_active():
                left = "left"
            else:
                left = "left to pay"
            if self.is_payment_sent() and not self.is_active():
                payment = "payment sent"
            elif self.is_paid():
                payment = "active"
            elif self.is_free():
                payment = "free"
            elif not self.is_active():
                payment = "notpaid"
            if self._data["expires"] - time.time() < 3600:
                tme = "%s seconds" % self.seconds_left()
            elif self._data["expires"] - time.time() < 3600 * 24:
                tme = "%s hours" % self.hours_left()
            else:
                tme = "%s days" % self.days_left()
            return "%s,%s %s" % (payment, tme, left)

    def is_fresh(self):
        return self._data["expires"] > time.time()

    def get_dict(self):
        data = copy(self._data)
        if "payment_sent" in data:
            del data["payment_sent"]
        return data

    def set_gate_data(self, gate, data):
        self._data[gate] = data

    def get_gate_data(self, gate):
        if gate in self._data:
            return self._data[gate]
        else:
            return False

    def get_pay_msgs(self):
        msgs = []
        m = lib.messages.Messages.pay([{
            "wallet": self._data["wallet"],
            "amount": self._data["price"]
        }], self.get_paymentid())
        msgs.append(m)
        if "contributions" in self._data:
            payments = []
            for s in self._data["contributions"]:
                payments.append({"wallet": s["wallet"], "amount": s["price"]})
                m = lib.messages.Messages.pay(payments, "0000000000000000")
                msgs.append(m)
        return msgs

    def __str__(self):
        return json.dumps(self._data)

    def get_title(self, short: bool = False):
        if short:
            txt = "sid=%s,%s" % (self.get_id(), self.pay_info())
        else:
            txt = "%s%s" % (self.get_gate(), self.get_space())
        return txt

    def validate(self):
        VDPObject.validate(self._data, "Session")

    def __repr__(self):
        try:
            txt = "Session-%s[%s/%s,days=%s,price=%s,payments=%s,paid=%s,fresh=%s]" % (self.get_id(), self.get_gate(), self.get_space(), self.days_left()
                                                                                       , self.get_price(), self.get_payment(), self.is_paid(), self.is_fresh())
        except Exception as e:
            txt = "Session[Empty]"
        return txt
