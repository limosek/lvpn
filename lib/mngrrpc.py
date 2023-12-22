import requests
import json


class ManagerRpcCall:

    def __init__(self, url):
        self._baseurl = url

    def parse_response(self, response):
        return json.loads(response)

    def preconnect(self, parameters):
        r = requests.post(
            self._baseurl + "/api/connect",
            headers={"Content-Type": "application/json"},
            json=parameters
        )
        return self.parse_response(r.text)

    def wait_for_connection(self, parameters):
        stripped = {
            "spaceid": parameters["spaceid"],
            "gateid": parameters["gateid"],
            "time": parameters["time"],
            "sessionid": parameters["sessionid"],
            "paymentid": parameters["paymentid"],
            "days": parameters["days"],
            "price": parameters["price"],
            "expires": parameters["expires"],
            "bearer": parameters["bearer"],
            "expires": parameters["expires"],
        }
        r = requests.post(
            self._baseurl + "/api/connect",
            headers={"Content-Type": "application/json"},
            json=parameters
        )
        if r.status_code == 200:
            return self.parse_response(r.text)
        elif r.status_code != 402:
            raise Exception("Bad response from manager: %s" % r.text)
        else:
            return False
