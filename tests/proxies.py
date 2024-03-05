import multiprocessing
import os
import unittest

os.environ["NO_KIVY"] = "1"

from client import Proxy
from lib.messages import Messages
from lib import Sessions, Session, Registry
from lib.queue import Queue
from client.connection import Connection
from client.tlsproxy import TLSProxy
from client.sshproxy import SSHProxy
from tests.util import Util

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TLSProxy2(TLSProxy):

    @classmethod
    def loop(cls):
        pass


class SSHProxy2(SSHProxy):

    @classmethod
    def loop(cls):
        pass


class Proxy2(Proxy):

    @classmethod
    def loop(cls, once=False):
        cls.exit = False
        super().loop(once=True)


class TestProxies(unittest.TestCase):

    def TLSproxy(self, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        sessions.load()
        ctrl = {}
        connection = Connection(session, port=8888)
        kwargs = {
            "endpoint": session.get_gate().get_endpoint(resolve=True),
            "ca": session.get_gate().get_ca(),
            "port": 8888,
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        TLSProxy2.run(ctrl, queue, queue2, **kwargs)

    def SSHproxy(self, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        sessions.load()
        ctrl = {}
        connection = Connection(session, port=8888)
        session = sessions.find(gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh")[0]
        kwargs = {
            "gate": session.get_gate(),
            "space": session.get_space(),
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        SSHProxy2.run(ctrl, queue, queue2, **kwargs)

    def testTlsProxy(self):
        Util.parse_args()
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 0)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        session.save()
        sessions.add(session)
        self.TLSproxy(session, sessions)

        session2 = Session()
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        session2.save()
        sessions.add(session2)
        self.TLSproxy(session2, sessions)

    def testProxyConnect(self):
        Util.parse_args()
        sessions = Sessions()
        ctrl = {}
        Messages.init_ctrl(ctrl)
        ctrl["cfg"] = Registry.cfg
        queue = Queue(multiprocessing.get_context(), "general")
        proxy_queue = Queue(multiprocessing.get_context(), "proxy")
        Proxy2.run(ctrl, queue, proxy_queue)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        sessions.add(session)
        proxy_queue.put(Messages.connect(session))
        Proxy2.loop(once=True)
        session2 = Session()
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        sessions.add(session2)
        proxy_queue.put(Messages.connect(session2))
        Proxy2.loop(once=True)
        Proxy2.loop(once=True)
        Proxy2.loop(once=True)
        Proxy2.loop(once=True)

        pass


if __name__ == "main":
    unittest.main()
