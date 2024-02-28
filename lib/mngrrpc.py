import logging
import requests
import json

from lib.gate import Gateway
from lib.registry import Registry
from lib.service import ServiceException
from lib.session import Session
from lib.space import Space
from lib.vdp import VDP
import client


class ManagerException(Exception):
    pass


class ManagerRpcCall:

    def __init__(self, url):
        self._baseurl = url

    def parse_response(self, response):
        return json.loads(response)

    def get_payment_url(self, wallet: str, paymentid: str) -> [str, bool]:
        r = requests.get(
            self._baseurl + "/api/pay/stripe?wallet=%s&paymentid=%s" % (wallet, paymentid)
        )
        if r.status_code == 200:
            return r.text
        else:
            logging.getLogger("client").error("Cannot get payment link: %s (%s)" % (r.status_code, r.text))
            return False

    def create_session(self, gate: Gateway, space: Space, days: int = None):
        session = Session()
        session.generate(gate.get_id(), space.get_id(), days)
        # Create fake session just for initializing data
        data = {"gateid": gate.get_id(), "spaceid": space.get_id(), "days": session.days()}
        if gate.get_type() == "wg" and Registry.cfg.enable_wg:
                data[gate.get_type()] = gate.get_prepare_data(session)
        r = requests.post(
            self._baseurl + "/api/session",
            headers={"Content-Type": "application/json"},
            json=data
        )
        if r.status_code == 200 or r.status_code == 402:
            return self.parse_response(r.text)
        else:
            raise ManagerException("%s -- %s" % (self._baseurl, r.text))

    def get_session_info(self, session):
        r = requests.get(
            self._baseurl + "/api/session?sessionid=%s" % session.get_id(),
        )
        if r.status_code == 200 or r.status_code == 402:
            return self.parse_response(r.text)
        elif r.status_code == 404:
            return None
        else:
            raise ManagerException("%s -- %s" % (self._baseurl, r.text))

    def push_vdp(self, vdp: VDP):
        vdp_jsn = vdp.get_json()
        try:
            r = requests.post(
                self._baseurl + "/api/vdp",
                data=vdp_jsn
            )
            if r.status_code == 200:
                return r.text
            else:
                raise ManagerException(r.text)
        except requests.RequestException as r:
            raise ManagerException("%s -- %s" % (self._baseurl, str(r)))

    def fetch_vdp(self):
        try:
            r = requests.get(
                self._baseurl + "/api/vdp"
            )
            if r.status_code == 200:
                return r.text
            else:
                raise ManagerException(r.text)
        except requests.RequestException as r:
            raise ManagerException("%s -- %s" % (self._baseurl, str(r)))

