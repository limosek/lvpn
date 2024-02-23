import time
from copy import copy

import stripe

from lib.registry import Registry
from lib.service import Service
from lib.messages import Messages


class StripeManager(Service):
    _messages = None
    myname = "stripemanager"

    @classmethod
    def postinit(cls):
        cls._messages = {}
        stripe.api_key = Registry.cfg.stripe_api_key

    @classmethod
    def loop(cls):
        skew = 3600 * 24 * 30
        while not cls.exit:
            plist = stripe.PaymentIntent.list(created={"gt": int(time.time() - skew)})
            cls.log_info("Found %s payments" % len(plist.data))
            for p in plist.data:
                cls.log_debug("Checking payment %s" % p["id"])
                if p["status"] != "succeeded":
                    cls.log_debug("Payment %s did not succeeded. Skipping" % p["id"])
                    continue
                if "metadata" in p:
                    if "paid" in p["metadata"]:
                        cls.log_info("Skipping paid payment %s" % p["id"])
                    elif "wallet" in p["metadata"] and "paymentid" in p["metadata"] and "amount1" in p["metadata"]:
                        wallet = p["metadata"]["wallet"]
                        amount1 = float(p["metadata"]["amount1"])
                        paymentid = p["metadata"]["paymentid"]
                        paid_amount = p["amount"] / 100
                        amount = paid_amount * amount1
                        metadata = copy(p["metadata"])
                        m = Messages.pay([{"wallet": wallet, "amount": amount}], paymentid=paymentid)
                        if m in cls._messages.keys():
                            cls.log_warning(
                                "Skipping payment waiting for confirmation: id=%s, wallet=%s,amount=%s,paymentid=%s" % (
                                    p["id"], wallet, amount, paymentid))
                        else:
                            cls.log_warning(
                                "Paying: id=%s, wallet=%s,amount=%s,paymentid=%s" % (
                                p["id"], wallet, amount, paymentid))
                            cls._messages[m] = {"id": p["id"], "metadata": metadata}
                            cls.queue.put(m)

            cls.update_old_plinks()
            for i in range(120):
                if not cls.myqueue.empty():
                    msg = cls.myqueue.get(block=False, timeout=0.01)
                    orig_msg = Messages.get_msg_data(msg)
                    if msg.startswith(Messages.PAID):
                        if orig_msg in cls._messages:
                            cls.set_as_paid(cls._messages[orig_msg]["id"], cls._messages[orig_msg]["metadata"])
                            del cls._messages[orig_msg]
                time.sleep(1)
            skew = 300

    @classmethod
    def update_old_plinks(cls):
        for p in Registry.cfg.stripe_plink_id.split(","):
            try:
                pl = stripe.PaymentLink.retrieve(p)
            except Exception as e:
                cls.log_error("Cannot retrieve payment link %s:%s" % (p, e))
                continue
            try:
                updated = float(pl.to_dict()["payment_intent_data"]["metadata"]["updated"])
            except Exception as e:
                cls.log_warning("Payment link without metadata:%s - will update" % p)
                continue
            if int(updated) + 600 < time.time():
                try:
                    stripe.PaymentLink.modify(p, active=False)
                except Exception as e:
                    cls.log_error("Cannot disable payment link %s:%s" % (p, e))

    @classmethod
    def set_as_paid(cls, id, metadata):
        metadata["paid"] = True
        try:
            p = stripe.PaymentIntent.retrieve(id)
            p.modify(p["id"], metadata=metadata)
        except Exception as e:
            cls.log_error(
                "Error when setting as paid: id=%s" % id)
        cls.log_warning(
            "Setting as paid: id=%s" % id)
