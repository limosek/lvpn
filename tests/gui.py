import multiprocessing
import os
import sys
import threading
import unittest

from kivy import Config
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout

import client
from lib import Registry
from lib.messages import Messages
from lib.queue import Queue
from tests.util import Util

try:
    import thread
except ImportError:
    import _thread as thread


def quit_function(fn_name):
    # print to stderr, unbuffered in Python 2.
    print('{0} took too long'.format(fn_name), file=sys.stderr)
    sys.stderr.flush() # Python 3 stderr is likely buffered.
    thread.interrupt_main() # raises KeyboardInterrupt


def exit_after(s):
    '''
    use as decorator to exit process if
    function takes longer than s seconds
    '''
    def outer(fn):
        def inner(*args, **kwargs):
            timer = threading.Timer(s, quit_function, args=[fn.__name__])
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result
        return inner
    return outer


class Switcher(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(App().get_running_app().stop, 5)


class PayBoxInfo(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(App().get_running_app().stop, 5)


class LVpn(App):

    def __init__(self, function):
        self._function = function
        super().__init__()

    def build(self):
        Config.set('graphics', 'width', '1200')
        Config.set('graphics', 'height', '700')
        Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

        return eval(self._function)


class TestGUI(unittest.TestCase):

    @classmethod
    def prepareGUI(cls):
        ctrl = {}
        Messages.init_ctrl(ctrl)
        client.gui.GUI.ctrl = ctrl
        client.gui.GUI.queue = Queue(multiprocessing.get_context(), "test1")
        client.gui.GUI.myqueue = Queue(multiprocessing.get_context(), "test2")
        Builder.load_file(Registry.cfg.app_dir + '/config/lvpn.kv')

    @classmethod
    def MainScreen(cls):
        LVpn("Switcher()").run()

    @classmethod
    def PayBoxScreen(cls):
        LVpn("PayBoxInfo()").run()

    def testScreens(self):
        Util.parse_args()
        self.prepareGUI()
        self.MainScreen()
        self.PayBoxScreen()

