import glob
import json
import logging
import os
import time

from lib.registry import Registry
from lib.session import Session
import lib


class Sessions:

    def __init__(self, cleanup=True, noload=False):
        self._sessions = {}
        if not noload:
            self.load(cleanup)

    def load(self, cleanup=False):
        for f in glob.glob(Registry.cfg.sessions_dir + "/*.lsession"):
            s = Session()
            try:
                s.load(f)
            except FileNotFoundError:
                self.remove(s)
                continue
            except json.JSONDecodeError:
                self.remove(s)
                continue
            if s.is_fresh():
                self._sessions[s.get_id()] = s
            else:
                if cleanup:
                    logging.getLogger("wallet").error("Cleaned session %s" % s.get_id())
                    self.remove(s)

    def save(self):
        for s in self.find():
            s.save()

    def cleanup(self):
        for s in self.find(active=True):
            self._sessions[s.get_id()] = s
        self.load(cleanup=True)

    def refresh_status(self):
        if Registry.cfg.is_client:
            for s in self.find(notpaid=True):
                mrpc = lib.mngrrpc.ManagerRpcCall(s.get_manager_url())
                try:
                    data = mrpc.get_session_info(s)
                    if data:
                        s = Session(data)
                        self.update(s)
                    else:
                        logging.getLogger().error("Session %s is not anymore on server. Deleting." % (s.get_id()))
                        self.remove(s)
                except Exception as e:
                    pass
                time.sleep(5)
        else:
            for s in self.find(inactive=True, fresh=True):
                if s.activate():
                    s.save()

    def get(self, sessionid: str):
        if sessionid in self._sessions.keys():
            return self._sessions[sessionid]
        else:
            f = Registry.cfg.sessions_dir + "/%s.lsession" % sessionid
            if os.path.exists(f):
                s = Session()
                try:
                    s.load(f)
                    self.update(s)
                    return s
                except Exception as e:
                    return False
            else:
                return False

    def find(self, notpaid=None, active=None, inactive=None, spaceid=None, gateid=None, fresh=None, paymentid=None, noparent=None, notfree=None, paid=None, free=None, needpay=None, wg_public=None):
        res = []
        for a in self._sessions.values():
            if notpaid and a.is_paid():
                continue
            if fresh and not a.is_fresh():
                continue
            if active and not a.is_active():
                continue
            if inactive and a.is_active():
                continue
            if spaceid and a.get_spaceid() != spaceid:
                continue
            if gateid and a.get_gateid() != gateid:
                continue
            if paymentid and not a.get_paymentid() == paymentid:
                continue
            if noparent and a.get_parent():
                continue
            if notfree and a.is_free():
                continue
            if paid and not a.is_paid():
                continue
            if free and not a.is_free():
                continue
            if needpay:
                if a.is_free() or a.is_paid():
                    continue
            if wg_public:
                if not a.get_gate_data("wg"):
                    continue
                else:
                    if a.get_gate_data("wg")["client_public_key"] != wg_public:
                        continue
            res.append(a)

        return sorted(res, key=lambda d: d.days_left())

    def add(self, session):
        self._sessions[session.get_id()] = session
        session.save()

    def remove(self, session):
        if session.get_id() in self._sessions:
            session.deactivate()
            del self._sessions[session.get_id()]
        if os.path.exists(session.get_filename()):
            os.unlink(session.get_filename())
        self.load()

    def update(self, session):
        self._sessions[session.get_id()] = session
        session.save()

    def process_payment(self, paymentid, amount, height, txid):
        sessions = self.find(paymentid=paymentid)
        updated = []
        for s in sessions:
            if s.add_payment(amount, height, txid):
                updated.append(s)
        if len(updated) == 0:
            logging.getLogger().debug("Paymentid %s did not match any session" % paymentid)
        else:
            self.load()
        return updated

    def __repr__(self):
        return "Sessions[all=%s,active=%s,free=%s,paid=%s,needpay=%s]" % (
            len(self.find()), len(self.find(active=True)), len(self.find(free=True)), len(self.find(paid=True)), len(self.find(needpay=True)))
