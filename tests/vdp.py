import os
os.environ["NO_KIVY"] = "1"

import unittest

from lib.registry import Registry
from tests.util import Util
from lib.vdp import VDP


class TestVDP(unittest.TestCase):

    def test_vdp_load(self):
        Util.parse_args()
        jsn = Registry.vdp.get_json()
        vdp2 = VDP(vdpdata=jsn)
        self.assertEqual(len(vdp2.gates()), 16)
        self.assertEqual(len(vdp2.spaces()), 2)
        self.assertEqual(len(vdp2.providers()), 1)

    def test_vdp_from_dirs(self):
        Util.parse_args()
        self.assertEqual(len(Registry.vdp.gates()), 16)
        self.assertEqual(len(Registry.vdp.spaces()), 2)
        self.assertEqual(len(Registry.vdp.providers()), 1)

    def test_get_ca(self):
        Util.parse_args()
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        a = gate.get_ca()
        self.assertEqual(type(a), str)

    def test_ro_providers(self):
        Util.parse_args(["--readonly-providers=94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091"])
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        old_endpoint = gate.get_endpoint()
        gate.set_endpoint("127.0.0.1", 1111)
        Registry.vdp.save()
        vdp = VDP()
        gate2 = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        self.assertEqual(old_endpoint, gate2.get_endpoint())
        pass

    def test_endpoint_resolve(self):
        Util.parse_args(["--readonly-providers=94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091"])
        gate = Registry.vdp.get_gate(
            "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy")
        e = gate.get_endpoint(resolve=True)
        pass


if __name__ == '__main__':
    unittest.main()
