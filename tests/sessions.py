import multiprocessing.queues
import os
import random
import secrets
import shutil
import time
import unittest

os.environ["NO_KIVY"] = "1"

from lib.session import Session
from lib.sessions import Sessions
from lib.registry import Registry
from tests.util import Util

if not "MANAGER_URL" in os.environ:
    os.environ["MANAGER_URL"] = "http://127.0.0.1:8123"


class TestSessions(unittest.TestCase):

    def testAll(self):
        Util.parse_args()
        Util.cleanup_sessions()
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 0)
        session = Session()
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session.save()
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 0)
        self.LoadSessions()
        self.PaySessions()
        self.LoadedSessions()
        self.Parent()
        left = self.Serialization()
        right = self.Concurrency()
        print(left, right)

    def LoadSessions(self):
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 1)

    def PaySessions(self):
        sessions = Sessions()
        session = sessions.find(notpaid=True)[0]
        paymentid = session.get_paymentid()
        self.assertEqual(session.get_payment(), 0)
        session.add_payment(1, 3737373, "txid")
        session.add_payment(1, 3737373, "txid")
        self.assertEqual(session.get_payment(), 1)
        session.add_payment(1, 3737374, "txid2")
        self.assertEqual(session.get_payment(), 2)
        sessions.process_payment(paymentid, 1, 433333, "txid3")
        session = sessions.get(session.get_id())
        self.assertEqual(session.get_payment(), 3)
        sessions.process_payment(paymentid, 1, 433333, "txid3")
        self.assertEqual(session.get_payment(), 3)
        self.assertEqual(len(sessions.find(notpaid=True)), 1)
        sessions.process_payment(paymentid, 31000, 433333, "txid4")
        session = sessions.get(session.get_id())
        self.assertEqual(session.get_payment(), 31003)
        self.assertTrue(session.is_paid(), True)
        self.assertTrue(session.is_fresh(), True)
        self.assertGreater(session.get_activation(), 10000)
        self.assertTrue(session.is_active(), True)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)
        self.assertEqual(len(sessions.find(active=True, spaceid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")), 1)
        Registry.cfg.contributions = "iz4LfSfmUJ6aSM1PA8d7wbexyouC87LdKACK76ooYWm6L1pkJRkBBh6Rk5Kh47bBc3ANCxoMKYbF7KgGATAANexg27PNTTa2j/developers/15%"
        Registry.cfg.is_client = False
        Registry.cfg.is_server = True
        session2 = Session()
        session2.generate(gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls", spaceid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", days=30)
        self.assertEqual(int(session2.get_price() + session2.get_contributions_price()), int(session.get_price()))
        Registry.cfg.contributions = "iz4LfSfmUJ6aSM1PA8d7wbexyouC87LdKACK76ooYWm6L1pkJRkBBh6Rk5Kh47bBc3ANCxoMKYbF7KgGATAANexg27PNTTa2j/developers/15%"
        Registry.cfg.is_client = True
        Registry.cfg.is_server = False
        session3 = Session()
        session3.generate(gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls", spaceid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", days=30)
        self.assertEqual(int(session3.get_price()), int(session.get_price() + session3.get_contributions_price()))
        Registry.cfg.is_client = False
        Registry.cfg.is_server = True

    def LoadedSessions(self):
        sessions = Sessions()
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)

    def Parent(self):
        sessions = Sessions()
        parent = Session()
        parent.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 1)
        parent.save()
        self.assertTrue(bool(parent.get_gate_data("ssh")))
        child = Session()
        child.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 1)
        child.set_parent(parent.get_id())
        child.save()
        child2 = Session()
        child2.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 1)
        child2.set_parent(parent.get_id())
        child2.save()
        self.assertFalse(bool(child.get_gate_data("proxy")))
        self.assertLess(len(sessions.find(active=True, noparent=True)), len(sessions.find(active=True)))

    def Concurrency(self):
        Util.cleanup_sessions()
        sr_init = repr(Sessions())
        ctrl = multiprocessing.Manager().dict()
        ctrl["cfg"] = Registry.cfg
        ctrl["vdp"] = Registry.vdp
        p1 = multiprocessing.Process(target=self.generate_unpaid_http, args=[ctrl])
        p1.start()
        p2 = multiprocessing.Process(target=self.generate_paid_free_socks, args=[ctrl])
        p2.start()
        p3 = multiprocessing.Process(target=self.generate_paid_free_ssh, args=[ctrl])
        p3.start()
        p4 = multiprocessing.Process(target=self.generate_unpaid_ssh, args=[ctrl])
        p4.start()
        p5 = multiprocessing.Process(target=self.pay_unpaid, args=[ctrl])
        p5.start()

        p1.join()
        p2.join()
        p3.join()
        p4.join()
        p5.join()

        sr_end = repr(Sessions())

        sr1 = self.sessions_from_array(ctrl["generate_unpaid_http"])
        sr2 = self.sessions_from_array(ctrl["generate_paid_free_socks"])
        sr3 = self.sessions_from_array(ctrl["generate_paid_free_ssh"])
        sr4 = self.sessions_from_array(ctrl["generate_unpaid_ssh"])
        print(sr_init)
        print(sr1)
        print(sr2)
        print(sr3)
        print(sr4)
        print(sr_end)
        self.assertEqual(len(Sessions().find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")),
                         ctrl["activated_ssh"])
        self.assertEqual(len(Sessions().find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")),
                         ctrl["activated_http"])
        return repr(Sessions())

    def Serialization(self):
        Util.cleanup_sessions()
        sr_init = repr(Sessions())

        ctrl = {"cfg": Registry.cfg, "vdp": Registry.vdp}
        self.generate_unpaid_http(ctrl)
        self.generate_paid_free_socks(ctrl)
        self.generate_paid_free_ssh(ctrl)
        self.generate_unpaid_ssh(ctrl)
        self.pay_unpaid(ctrl)

        sr_end = repr(Sessions())

        sr1 = self.sessions_from_array(ctrl["generate_unpaid_http"])
        sr2 = self.sessions_from_array(ctrl["generate_paid_free_socks"])
        sr3 = self.sessions_from_array(ctrl["generate_paid_free_ssh"])
        sr4 = self.sessions_from_array(ctrl["generate_unpaid_ssh"])
        print(sr_init)
        print(sr1)
        print(sr2)
        print(sr3)
        print(sr4)
        print(sr_end)
        self.assertEqual(len(Sessions().find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh")),
                         ctrl["activated_ssh"])
        self.assertEqual(len(Sessions().find(paid=True,
                                               gateid="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls")),
                         ctrl["activated_http"])
        return repr(Sessions())

    @classmethod
    def generate_unpaid_http(cls, ctrl):
        Registry.cfg = ctrl["cfg"]
        Registry.vdp = ctrl["vdp"]
        sessions = Sessions()
        sarr = []
        for i in range(2, 20):
            session = Session()
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy-tls",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", i)
            session.save()
            sarr.append(session)
            time.sleep(0.1)
        ctrl["generate_unpaid_http"] = sarr

    @classmethod
    def generate_paid_free_socks(cls, ctrl):
        Registry.cfg = ctrl["cfg"]
        Registry.vdp = ctrl["vdp"]
        sessions = Sessions()
        sarr = []
        for i in range(2, 20):
            session = Session()
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-socks-proxy",
                         "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 1)
            session.save()
            sarr.append(session)
            time.sleep(0.1)
        ctrl["generate_paid_free_socks"] = sarr

    @classmethod
    def generate_paid_free_ssh(cls, ctrl):
        Registry.cfg = ctrl["cfg"]
        Registry.vdp = ctrl["vdp"]
        sessions = Sessions()
        sarr = []
        for i in range(2, 20):
            session = Session()
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh",
                             "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free", 1)
            session.save()
            sarr.append(session)
            time.sleep(0.1)
        ctrl["generate_paid_free_ssh"] = sarr

    @classmethod
    def generate_unpaid_ssh(cls, ctrl):
        Registry.cfg = ctrl["cfg"]
        Registry.vdp = ctrl["vdp"]
        sessions = Sessions()
        sarr = []
        for i in range(2, 20):
            session = Session()
            session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.ssh",
                             "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", i)
            session.save()
            sarr.append(session)
            time.sleep(0.1)
        ctrl["generate_unpaid_ssh"] = sarr

    @classmethod
    def pay_unpaid(cls, ctrl):
        Registry.cfg = ctrl["cfg"]
        Registry.vdp = ctrl["vdp"]
        sessions = Sessions()
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
        ctrl["paid"] = paid
        ctrl["activated_ssh"] = activated_ssh
        ctrl["activated_http"] = activated_http

    @classmethod
    def sessions_from_array(cls, sarr):
        Util.cleanup_sessions()
        sessions = Sessions()
        for s in sarr:
            s.save()
        return repr(sessions)


if __name__ == "main":
    unittest.main()
