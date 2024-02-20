import json
import unittest
import os
import requests

from lib.vdp import VDP
from tests.vdp import TestVDP

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestAPI(unittest.TestCase):

    def testGetVdp(self):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/vdp",
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(r.status_code, 200)

    def testCheckVdp(self):
        vdp = VDP(TestVDP().parse_args([]))
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/vdp?checkOnly=True",
            headers={"Content-Type": "application/json"},
            data=vdp.get_json()
        )
        self.assertEqual(r.status_code, 200)
        bad = vdp.get_dict()
        bad["spaces"][0]["version"] = "bad_version_value"
        r = requests.post(
            os.environ["MANAGER_URL"] + "/api/vdp?checkOnly=True",
            headers={"Content-Type": "application/json"},
            data=bad
        )
        self.assertEqual(r.status_code, 443)


