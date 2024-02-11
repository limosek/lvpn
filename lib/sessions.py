import glob
import logging
import os

from lib.mngrrpc import ManagerRpcCall
from lib.session import Session


class Sessions:

    def __init__(self, cfg, cleanup=True):
        self._cfg = cfg
        self._sessions = {}
        self.load(cleanup)
        logging.getLogger("wallet").warning(repr(self))

    def load(self, cleanup=False):
        for f in glob.glob(self._cfg.sessions_dir + "/*.lsession"):
            s = Session(self._cfg)
            s.load(f)
            if s.is_fresh():
                self._sessions[s.get_id()] = s
            else:
                if cleanup:
                    logging.getLogger("wallet").error("Cleaned session %s" % s.get_id())
                    os.unlink(f)
                    self.remove(s)

    def save(self):
        for s in self.find():
            s.save()

    def cleanup(self):
        for s in self.find(active=True):
            self._sessions[s.get_id()] = s
        self.load(cleanup=True)

    def refresh_status(self):
        toremove = []
        for s in self.find(notpaid=True):
            mrpc = ManagerRpcCall(s.get_manager_url())
            try:
                data = mrpc.get_session_info(s)
                if data is None:
                    # Session not found on server - remove it
                    toremove.append(s)
                elif data:
                    s = Session(self._cfg, data)
                    self.update(s)
            except Exception as e:
                pass
        for s in toremove:
            self.remove(s)

    def get(self, sessionid):
        if sessionid in self._sessions.keys():
            return self._sessions[sessionid]
        else:
            f = self._cfg.sessions_dir + "/%s.lsession" % sessionid
            if os.path.exists(f):
                s = Session(self._cfg)
                s.load(f)
                self.update(s)
                return s
            else:
                return False

    def find(self, notpaid=None, active=None, spaceid=None, gateid=None, fresh=None, paymentid=None, noparent=None):
        res = []
        for a in self._sessions.values():
            if notpaid and a.is_paid():
                continue
            if fresh and not a.is_fresh():
                continue
            if active and not a.is_active():
                continue
            if spaceid and a.get_spaceid() != spaceid:
                continue
            if gateid and a.get_gateid() != gateid:
                continue
            if paymentid and not a.get_paymentid() == paymentid:
                continue
            if noparent and a.get_parent():
                continue
            res.append(a)

        return sorted(res, key=lambda d: d.days_left())

    def add(self, session):
        self._sessions[session.get_id()] = session
        session.save()

    def remove(self, session):
        if session.get_id() in self._sessions:
            del self._sessions[session.get_id()]
        if os.path.exists(session.get_filename()):
            os.unlink(session.get_filename())

    def update(self, session):
        self._sessions[session.get_id()] = session
        session.save()

    def process_payment(self, paymentid, amount, height, txid):
        for s in self.find(paymentid=paymentid):
            if s.add_payment(amount, height, txid):
                s.save()
                self.update(s)
                return s
            else:
                return False
        return False

    def __repr__(self):
        return "Sessions[all=%s,active=%s,notpaid=%s]" % (len(self.find()), len(self.find(active=True)), len(self.find(notpaid=True)))
