import logging
import multiprocessing
import os
import platform
import signal
import subprocess
import sys

from lib.registry import Registry


class RunCmd:

    cfg = None

    @classmethod
    def init(cls, cfg):
        Registry.cfg = cfg

    @classmethod
    def popen(cls, args, **kwargs):
        if platform.platform().lower().startswith("windows"):
            if Registry.cfg.l == "DEBUG":
                info = subprocess.STARTUPINFO()
            elif Registry.cfg.l == "INFO":
                SW_MINIMIZE = 6
                info = subprocess.STARTUPINFO()
                info.dwFlags = subprocess.STARTF_USESHOWWINDOW
                info.wShowWindow = SW_MINIMIZE
            else:
                SW_HIDE = 0
                info = subprocess.STARTUPINFO()
                info.dwFlags = subprocess.STARTF_USESHOWWINDOW
                info.wShowWindow = SW_HIDE
        else:
            info = None
        return subprocess.Popen(args, startupinfo=info, **kwargs)

    @classmethod
    def run(cls, args, **kwargs):
        return subprocess.Popen(args, **kwargs)

    @classmethod
    def get_output(cls, args, **kwargs):
        try:
            logging.getLogger().debug("runcmd: %s" % (" ".join(args)))
            ret = subprocess.check_output(args, universal_newlines=True, stderr=subprocess.PIPE, **kwargs)
            return ret
        except subprocess.CalledProcessError as e:
            logging.getLogger().error(e)
            print(e.stderr, file=sys.stderr)
            raise

    @classmethod
    def run_wait(cls, args, **kwargs):
        return os.system(" ".join(args))

    @classmethod
    def exec(cls, args):
        os.execvp(args[0], args)


class Process(multiprocessing.Process):

    def run(self):
        termmethod = self._target.__self__.sigterm
        signal.signal(signal.SIGTERM, termmethod)
        signal.signal(signal.SIGINT, termmethod)
        try:
            signal.signal(signal.CTRL_BREAK_EVENT, termmethod)
            signal.signal(signal.CTRL_C_EVENT, termmethod)
        except Exception:
            pass
        super().run()


