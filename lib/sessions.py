import json
import logging
import time

from lib.db import DB
from lib.registry import Registry
from lib.session import Session
import lib


class Sessions:

    def __init__(self):
        pass

    def cleanup(self):
        db = DB()
        db.begin()
        db.execute(
            "UPDATE sessions set deleted=True WHERE expires < %s" % time.time())
        db.execute(
            "DELETE FROM sessions WHERE deleted=True AND expires < %s" % (time.time() - 3600*24*30))
        db.commit()
        db.close()

    def refresh_status(self):
        self.cleanup()
        if Registry.cfg.is_client:
            for s in self.find(notpaid=True):
                mrpc = lib.mngrrpc.ManagerRpcCall(s.get_manager_url())
                try:
                    """Fetch session status from manager"""
                    data = mrpc.get_session_info(s)
                    time.sleep(30)
                    if data:
                        s = Session(data)
                        s.save()
                        logging.getLogger("audit").info("Updated session %s from server" % s.get_id())
                    else:
                        if s.get_created() < time.time():
                            if s.is_free():
                                time.sleep(120)
                                logging.getLogger().warning(
                                    "Free session %s is not anymore on server. Removing." % (s.get_id()))
                                s.remove()
                            else:
                                logging.getLogger("audit").error(
                                    "Paid session %s is not anymore on server!" % (s.get_id()))

                except lib.ManagerException as e:
                    logging.getLogger("vdp").error(str(e))
            for s in self.find(needs_reuse=True):
                mrpc = lib.mngrrpc.ManagerRpcCall(s.get_manager_url())
                try:
                    """Try to reuse session which will be over"""
                    data = mrpc.reuse_session(s)
                    if data:
                        s = Session(data)
                        s.save()
                        logging.getLogger("audit").info("Reused session %s" % s.get_id())
                except lib.ManagerException as e:
                    logging.getLogger("audit").error("Cannot reuse session %s: %s" % (s.get_id(), e))
        else:
            for s in self.find(inactive=True, fresh=True):
                s.activate()

    def get(self, sessionid: str):
        db = DB()
        data = db.select("SELECT data FROM sessions WHERE id='%s' AND DELETED IS FALSE" % sessionid)
        db.close()
        if len(data) > 0:
            return Session(json.loads(data[0][0]))
        else:
            return None

    def find(self, notpaid=None, active=None, inactive=None, spaceid=None, gateid=None, fresh=None, paymentid=None,
             noparent=None, notfree=None, paid=None, free=None, needpay=None, wg_public=None, needs_reuse=False):
        res = []
        ands = []
        db = DB()
        if active:
            ands.append("activated>0")
        if inactive:
            ands.append("activated=0")
        if spaceid:
            ands.append("spaceid='%s'" % spaceid)
        if gateid:
            ands.append("gateid='%s'" % gateid)
        if fresh:
            ands.append("expires>%s" % time.time())
        if paymentid:
            ands.append("paymentid='%s'" % paymentid)
        if noparent:
            ands.append("parent IS NULL")
        if notfree:
            ands.append("price>0")
        if free:
            ands.append("price=0")
        if paid:
            ands.append("paid IS TRUE")
        if notpaid:
            ands.append("paid IS FALSE")
        if needpay:
            ands.append("paid IS FALSE AND price>0")
        if wg_public:
            ands.append(db.cmp_str_attr("wg_public", wg_public))
        if needs_reuse:
            ands.append("expires>%s" % (time.time() - Registry.cfg.reuse_session_ahead))

        data = db.select("SELECT data FROM sessions WHERE deleted IS FALSE %s" % db.parse_ands(ands))
        db.close()
        for s in data:
            session = Session(json.loads(s[0]))
            if needs_reuse:
                if session.get_gate().get_type() != "wg":
                    # Only WG paid sessions needs reuse
                    continue
                else:
                    if session.is_free():
                        continue
            res.append(session)

        return res

    def process_payment(self, paymentid, amount, height, txid):
        sessions = self.find(paymentid=paymentid)
        updated = []
        for s in sessions:
            if s.add_payment(amount, height, txid):
                updated.append(s)
        if len(updated) == 0:
            # logging.getLogger("audit").debug("Paymentid %s did not match any session" % paymentid)
            pass
        return updated

    def __repr__(self):
        return "Sessions[all=%s,active=%s,free=%s,paid=%s,needpay=%s]" % (
            len(self.find()), len(self.find(active=True)), len(self.find(free=True)), len(self.find(paid=True)),
            len(self.find(needpay=True)))

    def __len__(self):
        db = DB()
        cnt = db.select("SELECT COUNT(*) FROM sessions WHERE expires>%s" % time.time())
        db.close()
        return cnt[0][0]
