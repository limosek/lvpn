import json
import os
import time
import unittest
import requests

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8124"


class TestClientAPI(unittest.TestCase):

    def testCreateFreeSession(self):
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/session",
            data=json.dumps({
                "gateid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                "spaceid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free",
                "days": 30
            }),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(r.text)
        self.assertEqual(j["price"], 0)
        self.assertEqual(j["paid"], True)
        self.assertLess(j["created"], time.time())
        self.GetPaidSession(j["sessionid"])

    def testCreatePaidSession(self):
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/session",
            data=json.dumps({
                "gateid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy",
                "spaceid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st",
                "days": 30
            }),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 402)
        j = json.loads(r.text)
        self.assertGreater(j["price"], 1)
        self.assertEqual(j["paid"], False)
        self.assertLess(j["created"], time.time())
        self.GetUnpaidSession(j["sessionid"])
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/pay/session/%s" % j["sessionid"],
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 200)
        pass

    def GetUnpaidSession(self, sessionid="1"):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/session?sessionid=%s" % sessionid
        )
        self.assertEqual(r.status_code, 402)
        j = json.loads(r.text)
        self.assertGreater(j["price"], 1)
        self.assertEqual(j["paid"], False)
        self.assertLess(j["created"], time.time())

    def GetPaidSession(self, sessionid="1"):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/session?sessionid=%s" % sessionid
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(r.text)
        self.assertEqual(j["paid"], True)
        self.assertLess(j["created"], time.time())
