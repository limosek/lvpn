from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
import logging

from client.gui_connect import Connect, PayBoxInfo
from client.gui_status import Status
from client.gui_wizard import Wizard
from client.gui_wallet import Wallet
import client
from lib.messages import Messages


class Switcher(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._status = Status()
        self._wizard = Wizard()
        self._connect = Connect()
        self._wallet = Wallet()
        self._connect.fill_gates(None, "")
        self._connect.fill_spaces(None, "")
        Clock.schedule_interval(self.switcher_loop, 1)
        Clock.schedule_interval(self._status.refresh_values, 3)

    def show_rootmenu(self):
        self.add_widget(Button(text="Main2"))

    def show_wizard(self):
        self.clear_widgets()
        self.add_widget(self._wizard)

    def show_status(self):
        self.clear_widgets()
        self.add_widget(self._status)

    def show_connect(self):
        self.clear_widgets()
        self.add_widget(self._connect)

    def show_wallet(self):
        self.clear_widgets()
        self.add_widget(self._wallet)

    def payboxinfo(self, session):
        self.clear_widgets()
        self.ids.connect_button.add_widget(PayBoxInfo(session))

    def switcher_loop(self, dt):
        if not client.gui.GUI.myqueue.empty():
            logging.getLogger("gui").debug("Switcher queue get")
            msg = client.gui.GUI.myqueue.get(block=False, timeout=0.01)
            if msg:
                if msg.startswith(Messages.GUI_POPUP):
                    data = Messages.get_msg_data(msg)
                    box = BoxLayout(orientation='vertical', padding=(10))
                    btn1 = Button(text="OK")
                    box.add_widget(btn1)
                    popup = Popup(title=data, title_size=(30),
                                  title_align='center', content=box)
                    btn1.bind(on_press=popup.dismiss)
                    popup.open()
                if msg.startswith(Messages.UNPAID):
                    data = Messages.get_msg_data(msg)
                    box = BoxLayout(orientation='vertical', padding=(10))
                    btn1 = Button(text="OK")
                    box.add_widget(btn1)
                    popup = Popup(title=data, title_size=(30),
                                  title_align='center', content=box)
                    btn1.bind(on_press=popup.dismiss)
                    popup.open()
