import os
import shutil
import unittest
import configargparse

os.environ["NO_KIVY"] = "1"

from client.connection import Connection
from lib.session import Session
from lib.sessions import Sessions
from lib.vdp import VDP

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestSessions(unittest.TestCase):

    def parse_args(self, args):
        p = configargparse.ArgParser(
            default_config_files=[])
        vardir = os.path.dirname(__file__)
        p.add_argument("--sessions-dir", help="Directory containing all spaces Sessions",
                       default=os.path.abspath(vardir + "/sessions"))
        p.add_argument("--spaces-dir", help="Directory containing all spaces VDPs",
                       default=os.path.abspath(vardir + "/../config/spaces"))
        p.add_argument("--gates-dir", help="Directory containing all gateway VDPs",
                       default=os.path.abspath(vardir + "/../config/gates"))
        p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                       default=os.path.abspath(vardir + "/../config/providers"))
        p.add_argument("--force-manager-wallet", default = False)
        p.add_argument("--unpaid-expiry", default=60)
        cfg = p.parse_args(args)
        return cfg

    def cleanup(self, cfg):
        if os.path.exists(cfg.sessions_dir):
            shutil.rmtree(cfg.sessions_dir)
        os.mkdir(cfg.sessions_dir)

    def testCreateConnection(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        cfg.connections = []
        self.cleanup(cfg)
        sessions = Sessions(cfg)
        cfg.sessions = sessions
        self.assertEqual(len(sessions.find()), 0)
        session = Session(cfg)
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session.save()
        sessions.add(session)
        connection = Connection(cfg, session, data={"endpoint": "aaa:1234"})
        self.assertEqual(connection.get_gate().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy")
        self.assertEqual(connection.get_space().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        c = connection.get_dict()
        conn2 = Connection(cfg, connection=c)
        self.assertEqual(conn2.get_space().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        conn2 = Connection(cfg, session=session, port=2222)
        conn2.set_data({"aa": "bb"})
        c = conn2.get_dict()
        d = Connection(cfg, connection=c)
        self.assertEqual(d.get_port(), 2222)
        pass


