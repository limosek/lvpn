import logging
import os
import secrets
import shutil
import glob


class Wizard:

    @staticmethod
    def files(cfg, vardir):
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
        for g in glob.glob(cfg.app_dir + "/config/gates/*lgate"):
            shutil.copy(g, cfg.gates_dir + "/")

        try:
            os.mkdir(cfg.spaces_dir)
        except FileExistsError as e:
            pass
        for s in glob.glob(cfg.app_dir + "/config/spaces/*lspace"):
            shutil.copy(s, cfg.spaces_dir + "/")
        try:
            os.mkdir(cfg.authids_dir)
        except FileExistsError as e:
            pass

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
