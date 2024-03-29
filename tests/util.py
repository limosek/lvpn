import logging
import os
import shutil

from lib import Sessions
from lib.db import DB

os.environ["NO_KIVY"] = "1"

import configargparse

from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from lib.registry import Registry
from lib.vdp import VDP
from lib.wizard import Wizard
from server.arguments import ServerArguments


class Util:

    @classmethod
    def parse_args(cls, args=[]):
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
        args.extend(["--wallet-rpc-password=1234", "--log-file=%s/tests.log" % vardir, "--log-level=INFO", "--force-manager-url", os.getenv("MANAGER_URL")])
        cfg = p.parse_args(args)
        cfg.l = cfg.log_level
        if os.path.exists("./var"):
            shutil.rmtree("./var")
        os.mkdir("./var")
        os.mkdir("./var/ssh")
        os.mkdir("./var/tmp")
        os.mkdir("./var/ca")
        Registry.cfg = cfg
        Wizard().files(cfg, vardir)
        Wizard().ssh_ca(cfg)
        Wizard().ca(cfg)
        cfg.is_server = True
        Registry.init(cfg, {}, None)
        sh = logging.StreamHandler()
        sh.setLevel(cfg.l)
        formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
        sh.setFormatter(formatter)
        logging.root.setLevel(logging.NOTSET)
        logging.basicConfig(level=logging.NOTSET, handlers=[sh])
        Registry.vdp = VDP()
        return cfg

    @classmethod
    def cleanup_sessions(self):
        db = DB()
        db.begin()
        db.execute("DELETE FROM sessions")
        db.commit()
        db.close()
        pass
