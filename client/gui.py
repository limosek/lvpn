import logging
import subprocess
import time
import threading
from kivy.app import App

# Must be here for msi builds
import kivy.weakmethod
import kivy.core.image

from lib.service import Service
import client


class LVpn(App):

    def build(self):
        return client.gui_switcher.Switcher()


class GUI(Service):
    myname = "gui"

    @classmethod
    def run_chromium(cls):
        args = [
            cls.ctrl["cfg"].chromium_bin,
            "--incognito",
            "--user-data-dir=%s" % cls.ctrl["cfg"].tmp_dir,
            "--proxy-server=http://localhost:8181",
            "https://www.seznam.cz"
        ]
        p = subprocess.run(args)

    @classmethod
    def postinit(cls):
        cls.processes = []
        b = threading.Thread(target=cls.loop)
        cls.processes.append(b)
        for p in cls.processes:
            p.start()
        LVpn().run()
        cls.exit = True

    @classmethod
    def loop(cls):
        while not cls.exit:
            time.sleep(1)

    @classmethod
    def stop(cls):
        super().stop()
        cls.exit = True
        for p in cls.processes:
            p.join()
