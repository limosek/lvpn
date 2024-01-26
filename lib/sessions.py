import glob
import logging
import os

from lib.session import Session


class Sessions:

    def __init__(self, cfg, cleanup=True):
        self._cfg = cfg
        self._sessions = {}
        self.load(cleanup)
        logging.getLogger("wallet").warning(repr(self))

    def load(self, cleanup=False):
        for f in glob.glob(self._cfg.sessions_dir + "/*.lsession"):
            s = Session(self._cfg).load(f)
            if s.is_fresh():
                self._sessions[s.get_id()] = s
            else:
                if cleanup:
                    logging.getLogger("wallet").error("Cleaned session %s" % s.get_id())
                    os.unlink(f)

    def cleanup(self):
        for s in self.find_active():
            self._sessions[s.get_id()] = s
        self.load(cleanup=True)

    def find_for_gate(self, gateid):
        res = []
        for a in self._sessions.keys():
            if a.is_fresh():
                if a.is_for_gate(gateid):
                    res.append(a)
            else:
                logging.getLogger("wallet").error("Stale session %s" % a.get_id())
        return sorted(res, key=lambda d: d.days_left())

    def find_by_paymentid(self, paymentid):
        for a in self._sessions.keys():
            if a.is_fresh():
                if a.get_paymentid() == paymentid:
                    return a
            else:
                logging.getLogger("wallet").error("Stale session %s" % a.get_id())

    def find_active(self):
        res = []
        for a in self._sessions.keys():
            if a.is_fresh():
                res.append(a)
            else:
                logging.getLogger("wallet").error("Stale session %s" % a.get_id())
        return sorted(res, key=lambda d: d.days_left())

    def __repr__(self):
        return "Sessions[all=%s,stale=%s]" % (len(self._sessions), len(self.find_active()))
