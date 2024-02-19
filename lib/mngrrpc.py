import logging

import requests
import json


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

    def create_session(self, gateid, spaceid, days):
        r = requests.post(
            self._baseurl + "/api/session",
            headers={"Content-Type": "application/json"},
            json={
                "gateid": gateid,
                "spaceid": spaceid,
                "days": days
            }
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
