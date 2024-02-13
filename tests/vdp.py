import os
import shutil
import unittest
from io import StringIO

import configargparse

from lib.vdp import VDP
from lib.wizard import Wizard


class TestVDP(unittest.TestCase):

    def parse_args(self, args):
        p = configargparse.ArgParser(
            default_config_files=[])
        p.add_argument("--spaces-dir", help="Directory containing all spaces VDPs",
                       default=os.path.abspath("./spaces"))
        p.add_argument("--gates-dir", help="Directory containing all gateway VDPs",
                       default=os.path.abspath("./gates"))
        p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                       default=os.path.abspath("./providers"))
        p.add_argument("--sessions-dir", help="Directory containing sessions",
                       default=os.path.abspath("./sessions"))
        p.add_argument('--readonly-providers',
                       help='List of providers, delimited by comma, which cannot be updated by VDP',
                       default="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091")
        cfg = p.parse_args(args)
        cfg.app_dir = ".."
        cfg.var_dir = "./"
        try:
            shutil.rmtree("./spaces")
        except FileNotFoundError:
            pass
        try:
            shutil.rmtree("./gates")
        except FileNotFoundError:
            pass
        try:
            shutil.rmtree("./providers")
        except FileNotFoundError:
            pass
        Wizard.files(cfg)
        cfg.readonly_providers = cfg.readonly_providers.split(",")

        return cfg

    def test_vdp_load(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        jsn = vdp.get_json()
        vdp2 = VDP(cfg, vdpdata=jsn)
        self.assertEqual(len(vdp2.gates()), 12)
        self.assertEqual(len(vdp2.spaces()), 2)
        self.assertEqual(len(vdp2.providers()), 1)

    def test_vdp_from_dirs(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        self.assertEqual(len(vdp.gates()), 12)
        self.assertEqual(len(vdp.spaces()), 2)
        self.assertEqual(len(vdp.providers()), 1)

    def test_get_ca(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        a = gate.get_ca()
        self.assertEqual(type(a), str)

    def test_ro_providers(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        old_endpoint = gate.get_endpoint()
        gate.set_endpoint("127.0.0.1", 1111)
        vdp.save()
        vdp = VDP(cfg)
        gate2 = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        self.assertEqual(old_endpoint, gate2.get_endpoint())
        pass

    def test_ro_providers2(self):
        cfg = self.parse_args([])
        cfg.readonly_providers = []
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        gate.set_endpoint("127.0.0.1", 1111)
        vdp.save()
        vdp = VDP(cfg)
        gate2 = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        self.assertEqual(gate.get_endpoint(), gate2.get_endpoint())
        pass


if __name__ == '__main__':
    unittest.main()
