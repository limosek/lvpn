import json
import os
import time
import unittest

import requests

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestStripeAPI(unittest.TestCase):

    def testGetPaymentLink(self):
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/pay/stripe?paymentid=%s&wallet=%s" % ("0000000000000000", "iz4LfSfmUJ6aSM1PA8d7wbexyouC87LdKACK76ooYWm6L1pkJRkBBh6Rk5Kh47bBc3ANCxoMKYbF7KgGATAANexg27PNTTa2j")
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text[:11], "https://buy")
        r = requests.get(
            os.environ["MANAGER_URL"] + "/api/pay/stripe?paymentid=%s&wallet=%s" % ("0000000000000000", "iz4LfSfmUJ6aSM1PA8d7wbexyouC87LdKACK76ooYWm6L1pkJRkBBh6Rk5Kh47bBc3ANCxoMKYbF7KgGATAANexg27PNTTa2j")
        )
        self.assertEqual(r.status_code, 502)


if __name__ == "main":
    unittest.main()
