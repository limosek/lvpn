import os
import shutil
import unittest

os.environ["NO_KIVY"] = "1"

import configargparse
from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from lib.vdp import VDP
from server.arguments import ServerArguments


class TestVDP(unittest.TestCase):

    def parse_args(self, args):
        p = configargparse.ArgParser(
            default_config_files=[])
        vardir = os.path.abspath("./var/")
        if os.path.exists(os.path.abspath(vardir + "/../config")):
            appdir = os.path.abspath(vardir + "/../")
        elif os.path.exists(os.path.dirname(__file__) + "/../config"):
            appdir = os.path.abspath(os.path.dirname(__file__) + "/../")
        else:
            appdir = os.path.abspath(os.environ["PYTHONPATH"])
        os.environ["WLS_CFG_DIR"] = os.path.abspath("./var/")
        p = SharedArguments.define(p, os.environ["WLS_CFG_DIR"], vardir, appdir, "WLS_", "server")
        p = ClientArguments.define(p, os.environ["WLS_CFG_DIR"], vardir, appdir)
        p = ServerArguments.define(p, os.environ["WLS_CFG_DIR"], vardir, appdir)
        args.extend(["--wallet-rpc-password=1234", "--log-file=%s/sessions.log" % vardir])
        cfg = p.parse_args(args)
        cfg.l = cfg.log_level
        cfg.readonly_providers = []
        if os.path.exists("./var"):
            shutil.rmtree("./var")
        os.mkdir("./var")
        os.mkdir("./var/sessions")
        os.mkdir("./var/providers")
        os.mkdir("./var/gates")
        os.mkdir("./var/spaces")
        os.mkdir("./var/ssh")
        os.mkdir("./var/tmp")
        os.mkdir("./var/ca")
        return cfg

    def test_vdp_load(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        jsn = vdp.get_json()
        vdp2 = VDP(cfg, vdpdata=jsn)
        self.assertEqual(len(vdp2.gates()), 15)
        self.assertEqual(len(vdp2.spaces()), 2)
        self.assertEqual(len(vdp2.providers()), 1)

    def test_vdp_from_dirs(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        self.assertEqual(len(vdp.gates()), 15)
        self.assertEqual(len(vdp.spaces()), 2)
        self.assertEqual(len(vdp.providers()), 1)

    def test_get_ca(self):
        cfg = self.parse_args([])
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        a = gate.get_ca()
        self.assertEqual(type(a), str)

    def test_ro_providers(self):
        cfg = self.parse_args(["--readonly-providers=94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091"])
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        old_endpoint = gate.get_endpoint()
        gate.set_endpoint("127.0.0.1", 1111)
        vdp.save()
        vdp = VDP(cfg)
        gate2 = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        self.assertEqual(old_endpoint, gate2.get_endpoint())
        pass


if __name__ == '__main__':
    unittest.main()
