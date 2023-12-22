import logging
import os
import shutil
import glob


class Wizard:

    @staticmethod
    def files(cfg, vardir):
        logging.getLogger().warning("Initializing default files")
        os.mkdir(vardir)
        os.mkdir("%s/tmp" % vardir)
        os.mkdir(cfg.gates_dir)
        for g in glob.glob(os.path.dirname(__file__) + "/../config/gates/*lgate"):
            shutil.copy(g, cfg.gates_dir + "/")
        os.mkdir(cfg.spaces_dir)
        for s in glob.glob(os.path.dirname(__file__) + "/../config/spaces/*lspace"):
            shutil.copy(s, cfg.spaces_dir + "/")
        os.mkdir(cfg.authids_dir)

