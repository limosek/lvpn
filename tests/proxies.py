import multiprocessing
import os
import sys
import threading
import time
import unittest
from copy import copy
import requests

os.environ["NO_KIVY"] = "1"

from client import Proxy
from lib.messages import Messages
from lib import Sessions, Session, Registry, ManagerRpcCall
from lib.queue import Queue
from client.connection import Connection
from client.tlsproxy import TLSProxy
from client.sshproxy import SSHProxy
from tests.util import Util
from lib.wg_engine import WGEngine
from server import WGServerService
from client.wg_service import WGClientService

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"

try:
    import thread
except ImportError:
    import _thread as thread


def quit_function(fn_name):
    # print to stderr, unbuffered in Python 2.
    print('{0} took too long'.format(fn_name), file=sys.stderr)
    sys.stderr.flush() # Python 3 stderr is likely buffered.
    thread.interrupt_main() # raises KeyboardInterrupt


def exit_after(s):
    '''
    use as decorator to exit process if
    function takes longer than s seconds
    '''
    def outer(fn):
        def inner(*args, **kwargs):
            timer = threading.Timer(s, quit_function, args=[fn.__name__])
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result
        return inner
    return outer


class SSHProxy2(SSHProxy):

    @classmethod
    def loop(cls):
        pass


class Proxy2(Proxy):

    @classmethod
    def loop(cls, once=False):
        cls.exit = False
        super().loop(once=once)


class TestProxies(unittest.TestCase):

    @exit_after(10)
    def runTLSproxy(self, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        ctrl = {}
        connection = Connection(session, port=8888)
        kwargs = {
            "endpoint": session.get_gate().get_endpoint(resolve=True),
            "ca": session.get_gate().get_ca(),
            "port": 8888,
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        TLSProxy.run(ctrl, queue, queue2, **kwargs)

    def runTLSproxy2(self, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        ctrl = {}
        connection = Connection(session, port=8888)
        kwargs = {
            "endpoint": session.get_gate().get_endpoint(resolve=True),
            "ca": session.get_gate().get_ca(),
            "port": 8888,
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        TLSProxy.run(ctrl, queue, queue2, **kwargs)

    @exit_after(10)
    def runSSHproxy(self, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
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

    @classmethod
    def requestor(cls, url, proxies):
        for i in range(1, 5):
            time.sleep(1)
            try:
                r = requests.request("GET", url, proxies=proxies)
                print(r.status_code)
            except Exception:
                pass

    def testTlsProxy1(self):
        Util.parse_args(["--single-thread=1"])
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 0)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        session.save()
        sessions.add(session)
        self.runTLSproxy(session, sessions)

        session2 = Session()
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                          "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        session2.save()
        sessions.add(session2)
        self.runTLSproxy(session2, sessions)

    def testTlsProxy2(self):
        Util.parse_args(["--single-thread=0"])
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 0)
        gate = Registry.vdp.get_gate(
            "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls")
        space = Registry.vdp.get_space(
            "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free")
        mr = ManagerRpcCall(space.get_manager_url())

        # Test bad certificate
        gate2 = copy(gate)
        gate2.set_endpoint("lethean.space", 443)
        session = Session(mr.create_session(gate2, space))
        session.save()
        sessions.add(session)
        #rp = multiprocessing.Process(target=self.requestor, args=["http://www.lthn/", {"http": "http://127.0.0.1:8888"}])
        #rp.start()
        #with self.assertRaises(ServiceException):
        #    self.runTLSproxy(session, sessions)

        # Test correct certificate
        session = Session(mr.create_session(gate2, space))
        session.save()
        sessions.add(session)
        with self.assertRaises(KeyboardInterrupt):
            self.runTLSproxy(session, sessions)

        # Test non-tls
        session2 = Session()
        session2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                          "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        session2.get_gate().set_endpoint("lethean.space", 80)
        session2.save()
        sessions.add(session2)
        with self.assertRaises(KeyboardInterrupt):
            self.runTLSproxy(session, sessions)
        pass

    def testProxyConnect(self):
        Util.parse_args()
        Util.cleanup_sessions()
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
        pass

    def testProxyConnectWg(self):
        Util.parse_args(["--enable-wg=1", "--single-thread=0"])
        Util.cleanup_sessions()
        sessions = Sessions()
        ctrl = multiprocessing.Manager().dict()
        Messages.init_ctrl(ctrl)
        ctrl["cfg"] = Registry.cfg
        WGEngine.show_cmds = True
        WGEngine.show_only = True
        queue = Queue(multiprocessing.get_context(), "general")
        proxy_queue = Queue(multiprocessing.get_context(), "proxy")
        Proxy2.run(ctrl, queue, proxy_queue)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        #WGServerService.prepare_server_session(session, {"public_key": "abcd"})
        #session.activate()
        session.save()
        proxy_queue.put(Messages.connect(session))
        # WG phase1
        Proxy2.loop(once=True)
        msg = queue.get()
        self.assertGreater(len(msg), 20)
        session = Messages.get_msg_data(msg)

        # WG phase2
        WGClientService.activate_on_client(session)

    def testRunRealProxy(self):
        Util.parse_args(["--enable-wg=1", "--single-thread=0"])
        Util.cleanup_sessions()
        sessions = Sessions()
        ctrl = multiprocessing.Manager().dict()
        Messages.init_ctrl(ctrl)
        ctrl["cfg"] = Registry.cfg
        gate = Registry.vdp.get_gate(
            "9c74b2e8d51fade774d00b07cfb4a91db424f6448cdcc2e83a26e0654031ce0a.http-proxy")
        space = Registry.vdp.get_space(
            "9c74b2e8d51fade774d00b07cfb4a91db424f6448cdcc2e83a26e0654031ce0a.free")
        mr = ManagerRpcCall(space.get_manager_url())
        session = Session(mr.create_session(gate, space))
        session.save()
        sessions.add(session)
        self.runTLSproxy2(session, sessions)


if __name__ == "main":
    unittest.main()
