import os
import unittest
from io import StringIO

import configargparse

from lib.vdp import VDP


class TestVDP(unittest.TestCase):

    def parse_args(self, args):
        p = configargparse.ArgParser(
            default_config_files=[])
        vardir = os.path.dirname(__file__) + "/../config/"
        p.add_argument("--spaces-dir", help="Directory containing all spaces VDPs",
                       default=os.path.abspath(vardir + "/spaces"))
        p.add_argument("--gates-dir", help="Directory containing all gateway VDPs",
                       default=os.path.abspath(vardir + "/gates"))
        p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                       default=os.path.abspath(vardir + "/providers"))
        cfg = p.parse_args(args)
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


if __name__ == '__main__':
    unittest.main()
