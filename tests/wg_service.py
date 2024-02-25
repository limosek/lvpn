import os
import shutil
import unittest

from client.wg_service import WGClientService
from lib.registry import Registry
from lib.session import Session
from lib.sessions import Sessions
from lib.wg_service import WGService
from server.wg_service import WGServerService

os.environ["NO_KIVY"] = "1"

from lib.service import ServiceException
from lib.wg_engine import WGEngine
import configargparse
from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from lib.vdp import VDP
from server.arguments import ServerArguments


class TestWGService(unittest.TestCase):

    @classmethod
    def parse_args(cls, args):
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
        Registry.cfg = self.parse_args([])
        Registry.vdp = VDP()
        WGEngine.show_cmds = True
        gate = Registry.vdp.get_gate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.wg")
        space = Registry.vdp.get_space("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        session = Session()
        session.generate(gate.get_id(), space.get_id(), 10)
        session = self.PrepareSession(session)
        self.ActivateServer(session)
        self.ActivateClient(session)
        self.DeActivateClient(session)
        self.DeActivateServer(session)

    def PrepareSession(self, session):
        WGServerService.prepare_server_session(session, {
            "endpoint": "dynamic",
            "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
        })
        self.assertEqual(session.get_gate_data("wg")["dns"], ["172.31.129.16"])
        self.assertEqual(session.get_gate_data("wg")["client_ipv4_address"], "10.169.0.2")
        WGServerService.prepare_server_session(session, {
            "endpoint": "abcd:123",
            "public_key": "84/GP/scO1E2oPcsQ7hds+rnR2SHGOr8CQ3hNAFn4Dk="
        })
        self.assertRegex(session.get_gate_data("wg")["client_endpoint"], "abcd")
        return session

    def ActivateServer(self, session):
        self.assertRegex(
            WGServerService.activate_on_server(session, show_only=True),
            "10.169.0.2")

    def ActivateClient(self, session):
        self.assertRegex(
            WGClientService.activate_on_client(session, show_only=True),
            "10.169.0.0/16")

    def DeActivateServer(self, session):
        self.assertRegex(
            WGServerService.deactivate_on_server(session, show_only=True),
            "84.*remove")

    def DeActivateClient(self, session):
        self.assertRegex(
            WGClientService.deactivate_on_client(session, show_only=True),
            session.get_gate_data("wg")["server_public_key"])

    def testPeersMatch(self):
        Registry.cfg = self.parse_args([])
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
        WGServerService.gate = gate
        peers1 = WGServerService.find_peers_from_sessions(sessions)
        peers2 = WGServerService.find_peers_from_gathered(
            WGEngine.gather_wg_data("ignored"),
            sessions
        )
        self.assertEqual(len(peers1), 2)
        self.assertEqual(len(peers2), 1)



