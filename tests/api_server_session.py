import json
import os
import time
import unittest
import requests

import lib.vdp
from client.wg_service import WGClientService
from lib import Session, ManagerRpcCall, Registry, ManagerException
from tests.util import Util

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestAPI(unittest.TestCase):

    def testCreateFreeSession(self):
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/session",
            data=json.dumps({
                "gateid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                "spaceid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free",
                "days": 1
            }),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(r.text)
        self.assertEqual(j["price"], 0)
        self.assertGreater(j["activated"], 0)
        self.assertLess(j["created"], time.time())
        self.GetPaidSession(j["sessionid"])

    def testCreateLongerFreeSession(self):
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/session",
            data=json.dumps({
                "gateid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                "spaceid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free",
                "days": 30
            }),
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 463)

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
        self.assertEqual(j["activated"], 0)
        self.assertLess(j["created"], time.time())
        self.GetUnpaidSession(j["sessionid"])

    def testCreateWgPaidSession(self):
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/session",
            data=json.dumps({
                "gateid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg",
                "spaceid": "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st",
                "days": 30,
                "wg": {
                    "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
                }
            }),
            headers={"Content-Type": "application/json"}
        )
        print(r.text)
        self.assertEqual(r.status_code, 402)
        j = json.loads(r.text)
        self.assertGreater(j["price"], 1)
        self.assertEqual(j["paid"], False)
        self.assertEqual(j["activated"], 0)
        self.assertLess(j["created"], time.time())
        self.assertEqual(j["wg"]["client_public_key"], "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=")
        self.assertEqual(j["wg"]["server_public_key"],  "oV6BmapVVfnFL0oKm4Ub0B7vaXwPlUZ0Y4mI+2VJxj8=")
        self.assertEqual(j["wg"]["ipv4_prefix"], 16)
        self.GetUnpaidSession(j["sessionid"])

    def GetUnpaidSession(self, sessionid="1"):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/session?sessionid=%s" % sessionid
        )
        self.assertEqual(r.status_code, 402)
        j = json.loads(r.text)
        self.assertGreater(j["price"], 1)
        self.assertEqual(j["activated"], 0)
        self.assertLess(j["created"], time.time())

    def GetPaidSession(self, sessionid="1"):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/session?sessionid=%s" % sessionid
        )
        self.assertEqual(r.status_code, 200)
        j = json.loads(r.text)
        self.assertGreater(j["activated"], 0)
        self.assertLess(j["created"], time.time())

    def test_vdp_from_url(self):
        vdp = lib.VDP("http://127.0.0.1:8123/api/vdp")
        pass

    def testRekeyReuseSession(self):
        Util.parse_args()
        m = ManagerRpcCall(os.environ["MANAGER_URL"])
        s1 = m.create_session(
            Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy"),
            Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"), 1)
        s1 = Session(s1)
        with self.assertRaises(ManagerException):
            m.rekey_session(s1, "aaaaaa")

        s2 = m.create_session(
            Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg"),
            Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"), 1, prepare_data={"wg": {
                "endpoint": "dynamic",
                "public_key": "uxn9r4nmw5GB1/+qoJnuVnk/bfReWkchI5O3DGwOLl4="
            }})

        s2 = Session(s2)
        self.assertEqual(s2.is_active(), True)
        s3 = m.rekey_session(s2, "mvaGhbvEHTfA+b5O5fAsE0dZKsd+WVEwsa2kmyPFV3A=")
        s3 = Session(s3)
        self.assertEqual(s3.get_gate_data("wg")["client_public_key"], "mvaGhbvEHTfA+b5O5fAsE0dZKsd+WVEwsa2kmyPFV3A=")

        with self.assertRaises(ManagerException):
            # Cannot reuse free session
            m.reuse_session(s3)

        s4 = m.create_session(
            Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg"),
            Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st"), 1, prepare_data={"wg": {
                "endpoint": "dynamic",
                "public_key": "mvaGhbvEHTfA+b5O5fAsE0dZKsd+WVEwsa2kmyPFV3A="
            }})

        s4 = Session(s4)
        with self.assertRaises(ManagerException):
            m.reuse_session(s4)

        pass


if __name__ == "main":
    unittest.main()
