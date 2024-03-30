import ipaddress
import os
import platform
import unittest

from tests.util import Util

os.environ["NO_KIVY"] = "1"

from client.wg_service import WGClientService
from lib.registry import Registry
from lib.session import Session
from lib.sessions import Sessions
from server.wg_service import WGServerService
from lib.wg_engine import WGEngine
from lib.vdp import VDP


class TestWGService(unittest.TestCase):

    def testAll(self):
        args = [
            "--wg-map-privkey=94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg,KA268iWOfG7M9vR/mAPdy5euxh1fDrZUHjVQFFwLxXY=",
            "--wg-cmd-route", "", "--enable-wg", "1"]
        if platform.system() == "Windows":
            args.extend(["--wg-cmd-prefix", "gsudo"])
        Registry.cfg = Util.parse_args(args)

        Registry.vdp = VDP()
        WGEngine.show_cmds = True
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        space = Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        session = Session()
        session.generate(gate.get_id(), space.get_id(), 10)
        WGEngine.create_wg_interface("lvpns_3e439354", WGEngine.get_private_key(gate.get_id()), 5000)
        self.FindIP()
        session = self.PrepareSession(session)
        self.ActivateServer(session)
        self.ActivateClient(session)
        self.DeActivateClient(session)
        self.DeActivateServer(session)

    def FindIP(self):
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        ip = WGServerService.find_free_ip(gate)
        ipv6 = WGServerService.find_free_ipv6(gate)
        pass

    def PrepareSession(self, session):
        WGServerService.prepare_server_session(session, {
            "endpoint": "dynamic",
            "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
        })
        self.assertEqual(session.get_gate_data("wg")["dns"], session.get_space()["dns_servers"])
        ip = ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"])
        ipnet = ipaddress.ip_network(
            session.get_gate_data("wg")["server_ipv4_address"] + "/" + str(session.get_gate_data("wg")["ipv4_prefix"]),
            strict=False)
        print(ip)
        print(ipnet)
        self.assertTrue(ip in ipnet)
        WGServerService.prepare_server_session(session, {
            "endpoint": "abcd:123",
            "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
        })
        self.assertRegex(session.get_gate_data("wg")["client_endpoint"], "abcd")
        return session

    def ActivateServer(self, session):
        print(WGServerService.activate_on_server(session, show_only=True))
        print(session.get_gate_data("wg")["server_ipv4_address"][:4])
        self.assertTrue(
            WGServerService.activate_on_server(session, show_only=True))
        pass

    def ActivateClient(self, session):
        self.assertTrue(WGClientService.activate_on_client(session, show_only=True))
        self.assertRegex(
            "\n".join(WGEngine.get_commands()),
            str(ipaddress.ip_network(session.get_gate_data("wg")["server_ipv4_address"] + "/" + str(
                session.get_gate_data("wg")["ipv4_prefix"]), strict=False)))

    def DeActivateServer(self, session):
        self.assertTrue(WGServerService.deactivate_on_server(session, show_only=True))
        self.assertRegex(
            "\n".join(WGEngine.get_commands()),
            "84.*remove")

    def DeActivateClient(self, session):
        self.assertTrue(WGClientService.deactivate_on_client(session, show_only=True))
        self.assertRegex(
            "\n".join(WGEngine.get_commands()),
            session.get_gate_data("wg")["server_public_key"][:7])

    def testPeersMatch(self):
        Registry.cfg = Util.parse_args([])
        Registry.vdp = VDP()
        WGEngine.show_cmds = True
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg")
        space = Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free")
        sessions = Sessions()
        session1 = Session()
        session1.generate(gate.get_id(), space.get_id(), 1)
        WGServerService.prepare_server_session(session1, {
            "endpoint": "dynamic",
            "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
        })
        session2 = Session()
        session2.generate(gate.get_id(), space.get_id(), 1)
        WGServerService.prepare_server_session(session2, {
            "endpoint": "dynamic",
            "public_key": "public2"
        })
        sessions.add(session1)
        sessions.add(session2)
        self.assertEqual(session1.activate(), True)
        self.assertEqual(session2.activate(), True)
