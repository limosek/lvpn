import os
import shutil
import unittest
import configargparse

os.environ["NO_KIVY"] = "1"

from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from server.arguments import ServerArguments
from client.connection import Connection, Connections
from lib.session import Session
from lib.sessions import Sessions
from lib.vdp import VDP

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestSessions(unittest.TestCase):

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

    def testReplaces(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        cfg.connections = []
        self.cleanup(cfg)
        sessions = Sessions(cfg)
        cfg.sessions = sessions
        self.assertEqual(len(sessions.find()), 0)
        session1 = Session(cfg)
        session1.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session1.save()
        sessions.add(session1)
        session2 = Session(cfg)
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session2.save()
        sessions.add(session1)

        connection1 = Connection(cfg, session1, data={"endpoint": "aaa:1234"})
        connection2 = Connection(cfg, session2, data={"endpoint": "aaa:1235"})
        connections = Connections(cfg)
        connections.add(connection1)
        connections.add(connection2)
        replace = connections.find_by_gateid("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")
        self.assertEqual(replace, connection2.get_id())
        replace = connections.find_by_gateid("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh")
        self.assertEqual(replace, connection1.get_id())
        data = connections.get_dict()
        connections2 = Connections(cfg, data)
        self.assertEqual(len(connections), len(connections2))
        pass


if __name__ == "main":
    unittest.main()
