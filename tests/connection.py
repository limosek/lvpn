import os
import shutil
import unittest
import configargparse

from lib.registry import Registry
from tests.util import Util

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


class TestConnections(unittest.TestCase):

    def cleanup(self, cfg):
        if os.path.exists(cfg.sessions_dir):
            shutil.rmtree(cfg.sessions_dir)
        os.mkdir(cfg.sessions_dir)

    def testCreateConnection(self):
        cfg = Util.parse_args([])
        cfg.connections = []
        self.cleanup(cfg)
        sessions = Sessions()
        cfg.sessions = sessions
        self.assertEqual(len(sessions.find()), 0)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session.save()
        connection = Connection(session, data={"endpoint": "aaa:1234"})
        self.assertEqual(connection.get_gate().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy")
        self.assertEqual(connection.get_space().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        c = connection.get_dict()
        conn2 = Connection(connection=c)
        self.assertEqual(conn2.get_space().get_id(),
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st")
        conn2 = Connection(session=session, port=2222)
        conn2.set_data({"aa": "bb"})
        c = conn2.get_dict()
        d = Connection(connection=c)
        self.assertEqual(d.get_port(), 2222)
        pass

    def testReplaces(self):
        cfg = Util.parse_args([])
        cfg.vdp = VDP()
        cfg.connections = []
        self.cleanup(cfg)
        sessions = Sessions()
        cfg.sessions = sessions
        self.assertEqual(len(sessions.find()), 0)
        session1 = Session()
        session1.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session1.save()
        session2 = Session()
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 1)
        session2.save()

        connection1 = Connection(session1, data={"endpoint": "aaa:1234"})
        connection2 = Connection(session2, data={"endpoint": "aaa:1235"})
        connections = Connections()
        connections.add(connection1)
        connections.add(connection2)
        conn = connections.find_by_gateid("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")
        self.assertEqual(conn, connection1.get_id())
        conn = connections.find_by_gateid("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh")
        self.assertEqual(conn, connection2.get_id())
        data = connections.get_dict()
        connections2 = Connections(data)
        self.assertEqual(len(connections), len(connections2))
        pass


if __name__ == "main":
    unittest.main()
