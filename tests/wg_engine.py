import hashlib
import ipaddress
import os
import shutil
import time
import unittest

os.environ["NO_KIVY"] = "1"
if not os.getenv("WG_DEV"):
    os.environ["WG_DEV"] = "test"

from lib.service import ServiceException
from lib.wg_engine import WGEngine
import configargparse
from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from lib.vdp import VDP
from server.arguments import ServerArguments


class TestWG(unittest.TestCase):

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

    def testAll(self):
        WGEngine.show_cmds = True
        try:
            self.DestroyInterface()
        except Exception as e:
            pass
        self.WgPrefix()
        self.CreateKeys()
        self.InterfaceName()
        self.CreateInterface()
        self.InterfaceIP()
        self.AddPeer()
        self.GatherInfo()
        self.DestroyInterface()

    def WgPrefix(self):
        cfg = self.parse_args(["--wg-cmd-prefix", "sh -c"])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        self.assertEqual(WGEngine.wg_run_cmd("wg", "show", show_only=True), "sh -c wg show")

    def CreateKeys(self):
        cfg = self.parse_args([])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        WGEngine.generate_keys()
        self.assertEqual(len(WGEngine.generate_keys()), 2)

    def InterfaceName(self):
        cfg = self.parse_args(["--wg-map-device", "aa"])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        with self.assertRaises(ServiceException):
            WGEngine.get_interface_name(gate.get_id())

        WGEngine.cfg = self.parse_args(["--wg-map-device", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,test"])
        self.assertEqual(WGEngine.get_interface_name(gate.get_id()), "test")
        gate2 = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy")
        self.assertEqual(WGEngine.get_interface_name(gate2.get_id()), hashlib.sha1(gate2.get_id().encode("utf-8")).hexdigest()[:8])

    def CreateInterface(self):
        cfg = self.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV")
                               ])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        private = WGEngine.generate_keys()[0]
        WGEngine.create_wg_interface(os.getenv("WG_DEV"), private=private, port=33333,
                                     ip=ipaddress.ip_address("1.2.3.4"), ipnet=ipaddress.ip_network("1.2.3.4/24", strict=False))

    def InterfaceIP(self):
        cfg = self.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV")
                               ])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        WGEngine.set_interface_ip(os.getenv("WG_DEV"), ip=ipaddress.ip_address("1.2.3.4"), ipnet=ipaddress.ip_network("1.2.3.0/24"))

    def AddPeer(self):
        cfg = self.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV")])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        WGEngine.add_peer(os.getenv("WG_DEV"), "82/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.4"], "10.10.10.10:1111",
                           "a8zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")
        WGEngine.add_peer(os.getenv("WG_DEV"), "83/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.5"], "10.10.10.11:1111",
                           "a7zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")
        WGEngine.add_peer(os.getenv("WG_DEV"), "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.6"], "10.10.10.12:1111",
                           "a5zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")

    def GatherInfo(self):
        cfg = self.parse_args(["--wg-map-device", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv("WG_DEV")])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        with self.assertRaises(ServiceException):
            WGEngine.gather_wg_data("abcd")
        info = WGEngine.gather_wg_data(os.getenv("WG_DEV"))
        self.assertEqual(info["iface"]["fwmark"], "off")
        self.assertEqual(len(info["peers"]), 3)
        print(info)

    def RemovePeer(self):
        cfg = self.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV")])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        vdp = VDP(cfg)
        gate = vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        info = WGEngine.remove_peer(gate.get_id(), "82/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=")
        info = WGEngine.gather_wg_data(gate.get_id())
        self.assertEqual(info["iface"]["fwmark"], "off")
        self.assertEqual(len(info["peers"]), 2)
        print(info)

    def DestroyInterface(self):
        cfg = self.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV")])
        WGEngine.cfg = cfg
        WGEngine.postinit()
        WGEngine.delete_wg_interface(os.getenv("WG_DEV"))


if __name__ == "main":
    unittest.main()
