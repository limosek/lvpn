import glob
import logging

from lib.authid import AuthID


class AuthIDs:

    def __init__(self, authids_dir):
        self._authids = []
        for f in glob.glob(authids_dir + "/*.authid"):
            authid = AuthID().load(f)
            self._authids.append(authid)

    def find_for_gate(self, gateid):
        res = []
        for a in self._authids:
            if a.is_fresh():
                if a.is_for_gate(gateid):
                    res.append(a)
            else:
                logging.getLogger("wallet").error("Stale authid %s" % a.get_id())
        return sorted(res, key=lambda d: d.days_left())

    def find(self, authid):
        for a in self._authids:
            if a.is_fresh():
                if a.get_id() == authid:
                    return a
            else:
                logging.getLogger("wallet").error("Stale authid %s" % a.get_id())
