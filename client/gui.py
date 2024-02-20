import time
import threading
from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config

from lib.runcmd import RunCmd
from lib.service import Service
import client


class LVpn(App):

    def build(self):
        Config.set('graphics', 'width', '1000')
        Config.set('graphics', 'height', '700')
        Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
        return client.gui_switcher.Switcher()


class GUI(Service):
    myname = "gui"

    @classmethod
    def postinit(cls):
        RunCmd.init(cls.cfg)
        cls.processes = []
        b = threading.Thread(target=cls.loop)
        cls.processes.append(b)
        for p in cls.processes:
            p.start()

        Builder.load_file(cls.cfg.app_dir + '/config/lvpn.kv')
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
