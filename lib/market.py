import json
import logging

import requests


class Market:

    @classmethod
    def get_price_tradeogre(cls, coin1, coin2):
        r = requests.get(
            "https://tradeogre.com/api/v1/markets"
        )
        if r.status_code == 200:
            mlist = json.loads(r.text)
            for m in mlist:
                pair1 = "%s-%s" % (coin1.upper(), coin2.upper())
                pair2 = "%s-%s" % (coin2.upper(), coin1.upper())
                if pair1 in m:
                    return float(m[pair1]["price"])
                elif pair2 in m:
                    return float(1/float(m[pair2]["price"]))
            logging.getLogger().error("Unknown combination of coins for market: %s-%s" % (coin1, coin2))
            return False

        else:
            logging.getLogger().error("Cannot get market price: code=%s" % r.status_code)
            return False

    @classmethod
    def get_price_coingecko(cls):
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "lethean",
            "vs_currencies": "EUR"
        }
        r = requests.get(url, params=params)
        if r.status_code == 200:
            rj = json.loads(r.text)
            return rj["lethean"]["eur"]
        else:
            logging.getLogger().error("Cannot get market price: code=%s" % r.status_code)
            return False
