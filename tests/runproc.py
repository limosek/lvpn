import os
import shutil
import unittest
import configargparse

os.environ["NO_KIVY"] = "1"

from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from lib.runcmd import RunCmd
from server.arguments import ServerArguments


class TestCmd(unittest.TestCase):

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

    def testSSH(self):
        cfg = self.parse_args([])
        RunCmd.init(cfg)
        a = RunCmd.get_output(["ls", "/"])
        self.assertGreater(len(a), 0)
        pass


