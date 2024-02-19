import multiprocessing.queues
import os
import random
import secrets
import shutil
import time
import unittest
import configargparse

os.environ["NO_KIVY"] = "1"

from client.arguments import ClientArguments
from server.arguments import ServerArguments
from lib.arguments import SharedArguments
from lib.queue import Queue
from client.connection import Connection
from client.tlsproxy import TLSProxy
from client.sshproxy import SSHProxy
from lib.session import Session
from lib.sessions import Sessions
from lib.vdp import VDP
from lib.wizard import Wizard

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
        if os.path.exists("./var"):
            shutil.rmtree("./var")
        os.mkdir("./var")
        os.mkdir("./var/sessions")
        os.mkdir("./var/ssh")
        os.mkdir("./var/tmp")
        os.mkdir("./var/ca")
        Wizard().ssh_ca(cfg)
        Wizard().ca(cfg)
        return cfg

    def cleanup_sessions(self):
        shutil.rmtree("./var/sessions")
        os.mkdir("./var/sessions")

    def testAll(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        self.cleanup_sessions()
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 0)
        session = Session(cfg)
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session.save()
        sessions.add(session)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 0)
        self.LoadSessions(cfg)
        self.PaySessions(cfg)
        self.LoadedSessions(cfg)
        self.Parent(cfg)
        self.TLSproxy(cfg, session, sessions)
        self.SSHproxy(cfg, session, sessions)
        left = self.Serialization(cfg)
        right = self.Concurrency(cfg)
        print(left, right)

    def LoadSessions(self, cfg):
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 1)

    def PaySessions(self, cfg):
        sessions = Sessions(cfg)
        session = sessions.find(notpaid=True)[0]
        paymentid = session.get_paymentid()
        self.assertEqual(session.get_payment(), 0)
        session.add_payment(1, 3737373, "txid")
        session.add_payment(1, 3737373, "txid")
        self.assertEqual(session.get_payment(), 1)
        session.add_payment(1, 3737374, "txid2")
        self.assertEqual(session.get_payment(), 2)
        sessions.process_payment(paymentid, 1, 433333, "txid3")
        sessions.update(session)
        self.assertEqual(session.get_payment(), 3)
        sessions.process_payment(paymentid, 1, 433333, "txid3")
        self.assertEqual(session.get_payment(), 3)
        self.assertEqual(len(sessions.find(notpaid=True)), 1)
        sessions.process_payment(paymentid, 3100, 433333, "txid4")
        self.assertEqual(session.get_payment(), 3103)
        self.assertTrue(session.is_paid(), True)
        self.assertTrue(session.is_fresh(), True)
        self.assertGreater(session.get_activation(), 10000)
        self.assertTrue(session.is_active(), True)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)
        self.assertEqual(len(sessions.find(active=True, spaceid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")), 1)
        sessions.save()

    def LoadedSessions(self, cfg):
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)

    def Parent(self, cfg):
        sessions = Sessions(cfg)
        parent = Session(cfg)
        parent.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        parent.save()
        self.assertTrue(bool(parent.get_gate_data("ssh")))
        child = Session(cfg)
        child.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        child.set_parent(parent.get_id())
        child.save()
        child2 = Session(cfg)
        child2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 30)
        child2.set_parent(parent.get_id())
        child2.save()
        self.assertFalse(bool(child.get_gate_data("proxy")))
        sessions.load()
        self.assertLess(len(sessions.find(active=True, noparent=True)), len(sessions.find(active=True)))

    def TLSproxy(self, cfg, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        sessions.load()
        cfg.sessions = sessions
        ctrl = {"cfg": cfg}
        connection = Connection(ctrl["cfg"], session, port=8888)
        kwargs = {
            "endpoint": session.get_gate().get_endpoint(resolve=True),
            "ca": session.get_gate().get_ca(),
            "port": 8888,
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        TLSProxy2.run(ctrl, queue, queue2, **kwargs)

    def SSHproxy(self, cfg, session, sessions):
        queue = Queue(multiprocessing.get_context(), "test1")
        queue2 = Queue(multiprocessing.get_context(), "test2")
        sessions.load()
        cfg.sessions = sessions
        ctrl = {"cfg": cfg}
        connection = Connection(ctrl["cfg"], session, port=8888)
        session = sessions.find(gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh")[0]
        kwargs = {
            "gate": session.get_gate(),
            "space": session.get_space(),
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        }
        #with self.assertRaises(sshtunnel.BaseSSHTunnelForwarderError):
        #    SSHProxy2.run(ctrl, queue, queue2, **kwargs)

    def Concurrency(self, cfg):
        self.cleanup_sessions()
        sessions_init = Sessions(cfg)
        ctrl = multiprocessing.Manager().dict()
        p1 = multiprocessing.Process(target=self.generate_unpaid_http, args=[cfg, ctrl])
        p1.start()
        p2 = multiprocessing.Process(target=self.generate_paid_free_socks, args=[cfg, ctrl])
        p2.start()
        p3 = multiprocessing.Process(target=self.generate_paid_free_ssh, args=[cfg, ctrl])
        p3.start()
        p4 = multiprocessing.Process(target=self.generate_unpaid_ssh, args=[cfg, ctrl])
        p4.start()
        p5 = multiprocessing.Process(target=self.pay_unpaid, args=[cfg, ctrl])
        p5.start()

        p1.join()
        p2.join()
        p3.join()
        p4.join()
        p5.join()

        sessions_end = Sessions(cfg)
        sessions_end.load()
        sessions_init.load()

        sessions1 = ctrl["generate_unpaid_http"]
        sessions1.load()
        sessions2 = ctrl["generate_paid_free_socks"]
        sessions2.load()
        sessions3 = ctrl["generate_paid_free_ssh"]
        sessions3.load()
        sessions4 = ctrl["generate_unpaid_ssh"]
        sessions4.load()
        sessions5 = ctrl["pay_unpaid"]
        sessions5.load()
        print(repr(sessions_init))
        print(repr(sessions1))
        print(repr(sessions2))
        print(repr(sessions3))
        print(repr(sessions4))
        print(repr(sessions5))
        print(repr(sessions_end))
        self.assertEqual(repr(sessions1), repr(sessions2))
        self.assertEqual(repr(sessions2), repr(sessions3))
        self.assertEqual(repr(sessions3), repr(sessions4))
        self.assertEqual(repr(sessions4), repr(sessions5))
        self.assertEqual(repr(sessions_init), repr(sessions1))
        self.assertEqual(repr(sessions_end), repr(sessions_init))
        self.assertEqual(len(sessions_end.find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")),
                         ctrl["activated_ssh"])
        self.assertEqual(len(sessions_end.find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")),
                         ctrl["activated_http"])
        return repr(sessions_end)

    def Serialization(self, cfg):
        self.cleanup_sessions()
        sessions_init = Sessions(cfg)

        ctrl = {}
        self.generate_unpaid_http(cfg, ctrl)
        self.generate_paid_free_socks(cfg, ctrl)
        self.generate_paid_free_ssh(cfg, ctrl)
        self.generate_unpaid_ssh(cfg, ctrl)
        self.pay_unpaid(cfg, ctrl)

        sessions_end = Sessions(cfg)
        sessions_end.load()
        sessions_init.load()

        sessions1 = ctrl["generate_unpaid_http"]
        sessions1.load()
        sessions2 = ctrl["generate_paid_free_socks"]
        sessions2.load()
        sessions3 = ctrl["generate_paid_free_ssh"]
        sessions3.load()
        sessions4 = ctrl["generate_unpaid_ssh"]
        sessions4.load()
        sessions5 = ctrl["pay_unpaid"]
        sessions5.load()
        print(repr(sessions_init))
        print(repr(sessions1))
        print(repr(sessions2))
        print(repr(sessions3))
        print(repr(sessions4))
        print(repr(sessions5))
        print(repr(sessions_end))
        self.assertEqual(repr(sessions1), repr(sessions2))
        self.assertEqual(repr(sessions2), repr(sessions3))
        self.assertEqual(repr(sessions3), repr(sessions4))
        self.assertEqual(repr(sessions4), repr(sessions5))
        self.assertEqual(repr(sessions_init), repr(sessions1))
        self.assertEqual(repr(sessions_end), repr(sessions_init))
        self.assertEqual(len(sessions_end.find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")),
                         ctrl["activated_ssh"])
        self.assertEqual(len(sessions_end.find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")),
                         ctrl["activated_http"])
        return repr(sessions_end)

    @classmethod
    def generate_unpaid_http(cls, cfg, ctrl):
        sessions = Sessions(cfg)
        for i in range(2, 20):
            session = Session(cfg)
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", i)
            sessions.add(session)
            time.sleep(0.1)
        ctrl["generate_unpaid_http"] = sessions

    @classmethod
    def generate_paid_free_socks(cls, cfg, ctrl):
        sessions = Sessions(cfg)
        for i in range(2, 20):
            session = Session(cfg)
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-socks-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", i)
            sessions.add(session)
            time.sleep(0.1)
        ctrl["generate_paid_free_socks"] = sessions

    @classmethod
    def generate_paid_free_ssh(cls, cfg, ctrl):
        sessions = Sessions(cfg)
        for i in range(2, 20):
            session = Session(cfg)
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                             "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", i)
            sessions.add(session)
            time.sleep(0.1)
        ctrl["generate_paid_free_ssh"] = sessions

    @classmethod
    def generate_unpaid_ssh(cls, cfg, ctrl):
        sessions = Sessions(cfg)
        for i in range(2, 20):
            session = Session(cfg)
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh",
                             "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", i)
            sessions.add(session)
            time.sleep(0.1)
        ctrl["generate_unpaid_ssh"] = sessions

    @classmethod
    def pay_unpaid(cls, cfg, ctrl):
        sessions = Sessions(cfg)
        paid = 0
        activated_ssh = 0
        activated_http = 0
        for i in range(2, 20):
            notpaid = sessions.find(notpaid=True, gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")
            if len(notpaid) > 0:
                paid += 1
                session = notpaid[0]
                paymentid = session.get_paymentid()
                sessions.process_payment(paymentid, session.get_price() / 3, random.randint(10000, 200000), secrets.token_hex(8))
                if session.is_active():
                    activated_ssh += 1
            notpaid = sessions.find(notpaid=True, gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")
            if len(notpaid) > 0:
                paid += 1
                session = notpaid[0]
                paymentid = session.get_paymentid()
                sessions.process_payment(paymentid, session.get_price() / 2, random.randint(10000, 200000), secrets.token_hex(8))
                if session.is_active():
                    activated_http += 1
            time.sleep(0.1)
        ctrl["pay_unpaid"] = sessions
        ctrl["paid"] = paid
        ctrl["activated_ssh"] = activated_ssh
        ctrl["activated_http"] = activated_http


if __name__ == "main":
    unittest.main()
