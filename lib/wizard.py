import logging
import os
import secrets
import shutil
import glob
from copy import copy

from lib.vdp import VDP


class Wizard:

    @staticmethod
    def files(cfg, vardir):
        cfgc = copy(cfg)
        logging.getLogger().warning("Initializing default files")
        try:
            os.mkdir(vardir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir("%s/tmp" % vardir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.gates_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.spaces_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.providers_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.authids_dir)
        except FileExistsError as e:
            pass

        cfgc.gates_dir = cfg.app_dir + "/config/gates/"
        cfgc.spaces_dir = cfg.app_dir + "/config/spaces/"
        cfgc.providers_dir = cfg.app_dir + "/config/providers/"
        v = VDP(cfgc)
        v.save(cfg)

    @staticmethod
    def cfg(cfg, p, vardir):
        if not cfg.wallet_password:
            cfg.wallet_password = secrets.token_urlsafe(12)
        with open(vardir + "/client.ini", "w") as f:
            f.write("""[global]
wallet-password = %s
wallet-rpc-password = %s
            """ % (cfg.wallet_password, cfg.wallet_rpc_password))
            pass
