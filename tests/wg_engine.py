import hashlib
import ipaddress
import os
import unittest

os.environ["NO_KIVY"] = "1"
if not os.getenv("WG_DEV"):
    os.environ["WG_DEV"] = "test"

from lib.service import ServiceException
from lib.wg_engine import WGEngine
from lib.registry import Registry
from tests.util import Util


class TestWG(unittest.TestCase):

    def testAll(self):
        Util.parse_args(["--enable-wg=1"])
        WGEngine.show_cmds = True
        try:
            self.DestroyInterface()
        except Exception as e:
            pass
        self.WgPrefix()
        Util.parse_args(["--enable-wg=1"])
        self.InterfaceName()
        Util.parse_args([])
        self.CreateKeys()
        self.CreateInterface()
        self.InterfaceIP()
        self.AddPeer()
        self.GatherInfo()
        self.DestroyInterface()

    def WgPrefix(self):
        Util.parse_args(["--enable-wg=1", "--wg-cmd-prefix", "sh -c"])
        self.assertEqual(WGEngine.wg_run_cmd("wg", "show", show_only=True), "sh -c wg show")

    def CreateKeys(self):
        WGEngine.generate_keys()
        self.assertEqual(len(WGEngine.generate_keys()), 2)

    def InterfaceName(self):
        Util.parse_args(["--wg-map-device", "aa"])
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        with self.assertRaises(ServiceException):
            WGEngine.get_interface_name(gate.get_id())

        Util.parse_args(["--wg-map-device", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,test"])
        self.assertEqual(WGEngine.get_interface_name(gate.get_id()), "test")
        gate2 = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy")
        self.assertEqual(WGEngine.get_interface_name(gate2.get_id()), hashlib.sha1(gate2.get_id().encode("utf-8")).hexdigest()[:8])

    def CreateInterface(self):
        Util.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv("WG_DEV"), "--enable-wg=1"])
        private = WGEngine.generate_keys()[0]
        WGEngine.create_wg_interface(os.getenv("WG_DEV"), private=private, port=33333)

    def InterfaceIP(self):
        Util.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv("WG_DEV"), "--enable-wg=1"])
        WGEngine.set_interface_ip(os.getenv("WG_DEV"), ip=ipaddress.ip_address("2.2.3.4"), ipnet=ipaddress.ip_network("2.2.3.0/24"))

    def AddPeer(self):
        Util.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV"), "--enable-wg=1"])
        WGEngine.add_peer(os.getenv("WG_DEV"), "82/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.4"], "10.10.10.10:1111",
                           "a8zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")
        WGEngine.add_peer(os.getenv("WG_DEV"), "83/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.5"], "10.10.10.11:1111",
                           "a7zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")
        WGEngine.add_peer(os.getenv("WG_DEV"), "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=", ["1.2.3.6"], "10.10.10.12:1111",
                           "a5zIhpHsqUfawuo+x7EagPL21yzmjkrKMxPfLS5r72A=")

    def GatherInfo(self):
        Util.parse_args(["--wg-map-device", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv("WG_DEV"), "--enable-wg=1"])
        with self.assertRaises(ServiceException):
            WGEngine.gather_wg_data("abcd")
        info = WGEngine.gather_wg_data(os.getenv("WG_DEV"))
        self.assertEqual(info["iface"]["fwmark"], "off")
        self.assertEqual(len(info["peers"]), 3)
        print(info)

    def RemovePeer(self):
        Util.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV"), "--enable-wg=1"])
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        WGEngine.remove_peer(gate.get_id(), "82/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk=")
        info = WGEngine.gather_wg_data(gate.get_id())
        self.assertEqual(info["iface"]["fwmark"], "off")
        self.assertEqual(len(info["peers"]), 2)
        print(info)

    def DestroyInterface(self):
        Util.parse_args(["--wg-map-device",
                               "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,%s" % os.getenv(
                                   "WG_DEV"), "--enable-wg=1"])
        WGEngine.delete_wg_interface(os.getenv("WG_DEV"))


if __name__ == "main":
    unittest.main()
