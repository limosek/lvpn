import logging
import requests
import json

from lib.gate import Gateway
from lib.space import Space
from lib.vdp import VDP
import lib


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

    def create_session(self, gate: Gateway, space: Space, days: int):
        data = {
                "gateid": gate.get_id(),
                "spaceid": space.get_id(),
                "days": days
            }
        if gate.get_type() == "wg":
            data["wg"] = lib.wg_service.WGService.prepare_session_request(gate)
        r = requests.post(
            self._baseurl + "/api/session",
            headers={"Content-Type": "application/json"},
            json=data
        )
        if r.status_code == 200 or r.status_code == 402:
            return self.parse_response(r.text)
        else:
            raise ManagerException(r.text)

    def get_session_info(self, session):
        r = requests.get(
            self._baseurl + "/api/session?sessionid=%s" % session.get_id(),
        )
        if r.status_code == 200 or r.status_code == 402:
            return self.parse_response(r.text)
        elif r.status_code == 404:
            return None
        else:
            raise ManagerException(r.text)

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
            raise ManagerException(str(r))

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
            raise ManagerException(str(r))