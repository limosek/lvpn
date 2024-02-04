import logging
import platform
import subprocess


class RunCmd:

    cfg = None

    @classmethod
    def init(cls, cfg):
        cls.cfg = cfg

    @classmethod
    def popen(cls, args, **kwargs):
        if platform.platform().lower().startswith("windows"):
            if cls.cfg.l == "DEBUG":
                info = subprocess.STARTUPINFO()
            elif cls.cfg.l == "INFO":
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
