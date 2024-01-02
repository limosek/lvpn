import subprocess


class RunCmd:

    cfg = None

    @classmethod
    def init(cls, cfg):
        cls.cfg = cfg

    @classmethod
    def popen(cls, args, **kwargs):
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
        return subprocess.Popen(args, startupinfo=info, **kwargs)
