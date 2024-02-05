import os
import shutil
import unittest

import configargparse

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

    def testCreateSession(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        self.cleanup(cfg)
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 0)
        session = Session(cfg)
        session.generate("94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.http-proxy", "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.1st", 30)
        session.save()
        sessions.add(session)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 0)

    def testLoadSessions(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 1)

    def testPaySessions(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
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
        sessions.process_payment(paymentid, 10, 433333, "txid3")
        self.assertEqual(session.get_payment(), 13)
        self.assertTrue(session.is_paid(), True)
        self.assertTrue(session.is_fresh(), True)
        self.assertGreater(session.get_activation(), 10000)
        self.assertTrue(session.is_active(), True)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)
        sessions.save()

    def testLoadedSessions(self):
        cfg = self.parse_args([])
        cfg.vdp = VDP(cfg)
        sessions = Sessions(cfg)
        self.assertEqual(len(sessions.find()), 1)
        self.assertEqual(len(sessions.find(active=True)), 1)
        self.assertEqual(len(sessions.find(notpaid=True)), 0)

