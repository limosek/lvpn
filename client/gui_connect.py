import logging
import shutil

import requests.exceptions
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton

import client
import lib.mngrrpc
from lib.registry import Registry
from lib.runcmd import RunCmd
from lib.session import Session
from lib.sessions import Sessions
from lib.messages import Messages


class SpaceButton(ToggleButton):
    def __init__(self, spaceid, **kwargs):
        super().__init__(group='spaces', **kwargs)
        self.spaceid = spaceid


class GateButton(ToggleButton):
    def __init__(self, gateid, **kwargs):
        super().__init__(group='gates', **kwargs)
        self.gateid = gateid


class DisconnectButton(Button):
    def __init__(self, connection, **kwargs):
        super().__init__(**kwargs)
        self.connection = connection


class BrowserButton(Button):
    def __init__(self, proxy=None, url=None, **kwargs):
        super().__init__(**kwargs)
        self.proxy = proxy
        self.url = url


class PayButton(Button):
    def __init__(self, gateid, spaceid, days, **kwargs):
        super().__init__(**kwargs)
        self._spaceid = spaceid
        self._gateid = gateid
        self._days = days


class ConnectionButton(Button):
    def __init__(self, gateid, spaceid, **kwargs):
        super().__init__(**kwargs)
        self.spaceid = spaceid
        self.gateid = gateid


class Connect(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.gate_filter.bind(text=self.fill_gates)
        self.ids.space_filter.bind(text=self.fill_spaces)
        self.ids.connect_button.bind(on_press=self.connect)
        Clock.schedule_interval(self.fill_connections, 1)
        Clock.schedule_interval(self.update_gate_info, 2)

    def connect(self, instance):
        logging.getLogger("gui").info("Connect %s/%s" % (client.gui.GUI.ctrl["selected_gate"], client.gui.GUI.ctrl["selected_space"]))
        sessions = Sessions()
        asessions = sessions.find(gateid=client.gui.GUI.ctrl["selected_gate"], spaceid=client.gui.GUI.ctrl["selected_space"], active=True)
        if len(asessions) > 0:
            client.gui.GUI.queue.put(Messages.connect(asessions[0]))
        else:
            space = Registry.vdp.get_space(client.gui.GUI.ctrl["selected_space"])
            mr = lib.ManagerRpcCall(space.get_manager_url())
            try:
                gate = Registry.vdp.get_gate(client.gui.GUI.ctrl["selected_gate"])
                space = Registry.vdp.get_space(client.gui.GUI.ctrl["selected_space"])
                session = Session(mr.create_session(gate, space))
                session.save()
                client.gui.GUI.queue.put(Messages.connect(session))
            except requests.exceptions.RequestException as e:
                logging.getLogger("gui").error("Cannot connect to %s/%s: %s" % (client.gui.GUI.ctrl["selected_gate"], client.gui.GUI.ctrl["selected_space"], e))
                client.gui.GUI.queue.put(Messages.gui_popup("Cannot connect to %s/%s: %s" % (client.gui.GUI.ctrl["selected_gate"], client.gui.GUI.ctrl["selected_space"], e)))

    def disconnect(self, instance):
        logging.getLogger("gui").warning("Disconnect %s" % (instance.connection))
        client.gui.GUI.queue.put(Messages.disconnect(instance.connection.get_id()))

    @classmethod
    def run_edge(cls, instance, incognito: bool = True):
        if incognito:
            incognito = "--inprivate"
        args = [Registry.cfg.edge_bin]
        if incognito:
            args.append(incognito)
            args.append("--user-data-dir=%s" % Registry.cfg.tmp_dir)
        if instance.proxy:
            args.append("--proxy-server=%s" % instance.proxy)
        args.append(instance.url)
        logging.getLogger().debug("Running %s" % " ".join(args))
        try:
            RunCmd.run(args, shell=False)
        except Exception as e:
            logging.getLogger("gui").error(e)

    @classmethod
    def run_chromium(cls, instance, incognito: bool = True):
        if incognito:
            incognito = "--incognito"
        args = [Registry.cfg.chromium_bin]
        if incognito:
            args.append(incognito)
            args.append("--user-data-dir=%s" % Registry.cfg.tmp_dir)
        if instance.proxy:
            args.append("--proxy-server=%s" % instance.proxy)
        args.append(instance.url)
        logging.getLogger().debug("Running %s" % " ".join(args))
        try:
            RunCmd.run(args, shell=False)
        except Exception as e:
            logging.getLogger("gui").error(e)

    @classmethod
    def run_browser(cls, instance, incognito=True):
        if shutil.which(Registry.cfg.chromium_bin):
            cls.run_chromium(instance, incognito=incognito)
        elif shutil.which(Registry.cfg.edge_bin):
            cls.run_edge(instance, incognito=incognito)
        else:
            pass

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def pay_service(self, instance):
        space = Registry.vdp.get_space(instance._spaceid)
        gate = Registry.vdp.get_gate(instance._gateid)
        try:
            mngr = ManagerRpcCall(space.get_manager_url())
            data = mngr.create_session(gate, space, instance._days)
            session = Session(data=data)
            session.save()
            if not session.is_paid():
                client.gui.GUI.queue.put(session.get_pay_msg())
        except Exception as e:
            logging.getLogger("gui").error("Cannot prepare payment: %s" % e)

    def select_space(self, instance):
        if instance.state == "down":
            client.gui.GUI.ctrl["selected_space"] = instance.spaceid
        else:
            client.gui.GUI.ctrl["selected_space"] = None
            self.ids.pay_1.disabled = True
            self.ids.pay_30.disabled = True
        self.fill_gates(None, None)
        self.ids.connect_button.disabled = True
        self.ids.payment_state.text = "Unknown"

    def update_gate_info(self, old):
        if client.gui.GUI.ctrl["selected_gate"] and client.gui.GUI.ctrl["selected_space"]:
            gateid = client.gui.GUI.ctrl["selected_gate"]
            spaceid = client.gui.GUI.ctrl["selected_space"]
            self.select_gate(None, gateid, spaceid)
        else:
            return

    def select_gate(self, instance, gateid=None, spaceid=None):
        if instance:
            spaceid = instance.spaceid
            gateid = instance.gateid
        try:
            sessions = Sessions()
            if not instance or instance.state == "down":
                client.gui.GUI.ctrl["selected_gate"] = gateid
                self.ids.connect_button.disabled = False
                asessions = sessions.find(gateid=gateid, spaceid=spaceid, active=True)
                fsessions = sessions.find(gateid=gateid, spaceid=spaceid, fresh=True)
                space = Registry.vdp.get_space(spaceid)
                gate = Registry.vdp.get_gate(gateid)
                if not space or not gate:
                    return
                if (space.get_price() + gate.get_price()) == 0:
                    self.ids.pay_1.disabled = True
                    self.ids.pay_30.disabled = True
                else:
                    if len(asessions) > 0:
                        self.ids.pay_1.disabled = True
                        self.ids.pay_30.disabled = True
                        self.ids.connect_button.disabled = False
                    else:
                        self.ids.pay_1.disabled = False
                        self.ids.pay_30.disabled = False
                        self.ids.connect_button.disabled = True
                        self.ids.pay_buttons.clear_widgets()
                        pay_1 = PayButton(text="Pay 1 day", gateid=gateid,
                                          spaceid=spaceid, days=1, on_press=self.pay_service)
                        pay_30 = PayButton(text="Pay 30 days", gateid=gateid,
                                           spaceid=spaceid, days=30,
                                           on_press=self.pay_service)
                        self.ids.pay_buttons.add_widget(pay_1)
                        self.ids.pay_buttons.add_widget(pay_30)
                        self.ids.connect_button.disabled = True
                        self.ids.payment_state.text = "Not paid (%.1f/%.1f per day)" % (space.get_price(), gate.get_price())
                if len(fsessions) > 0:
                    if len(asessions) > 0:
                        session = asessions[0]
                    else:
                        session = fsessions[0]
                    self.ids.payment_state.text = "%s" % session.pay_info()
                    if len(asessions) > 0:
                        self.ids.connect_button.disabled = False
                    else:
                        self.ids.connect_button.disabled = True
                else:
                    self.ids.connect_button.disabled = False
            else:
                self.ids.connect_button.disabled = True
                self.ids.payment_state.text = "Unknown"
        except ReferenceError:
            logging.getLogger().error("Error updating GUI.")

    def fill_gates(self, instance=None, value=None, selected=None):
        self.ids.choose_gate.clear_widgets()
        if client.gui.GUI.ctrl["selected_space"]:
            disabled = False
        else:
            disabled = True
        for g in Registry.vdp.gates(self.ids.gate_filter.text, client.gui.GUI.ctrl["selected_space"], internal=False):
            if selected and selected == g.get_id():
                state = "down"
            else:
                state = "normal"
            btn = GateButton(text=g.get_name(), on_press=self.select_gate, gateid=g.get_id(), disabled=disabled, state=state)
            setattr(self.ids, g.get_id(), btn)
            self.ids.choose_gate.add_widget(btn)

    def fill_spaces(self, instance=None, value=None, selected=None):
        self.ids.choose_space.clear_widgets()
        for s in Registry.vdp.spaces(self.ids.space_filter.text):
            if selected and selected == s.get_id():
                state = "down"
            else:
                state = "normal"
            btn = SpaceButton(text=s.get_name(), on_press=self.select_space, spaceid=s.get_id(), state=state)
            setattr(self.ids, s.get_id(), btn)
            self.ids.choose_space.add_widget(btn)

    def fill_connections(self, dt):
        self.ids.connections_info.clear_widgets()
        for c in client.gui.GUI.ctrl["connections"]:
            row = GridLayout(cols=3, rows=1, size_hint_y=0.2)
            if c.get_gate().is_internal():
                lbl = Label(text=c.get_title(short=True), color=(0.2, 0.2, 2))
            else:
                lbl = ConnectionButton(text=c.get_title(short=True),
                                  spaceid=c.get_space().get_id(),
                                  gateid=c.get_gate().get_id(),
                                  on_press=self.show_connection)
            row.add_widget(lbl)
            if c.get_gate().get_type() == "http-proxy":
                bbtn = BrowserButton(text="Run browser", proxy="http://127.0.0.1:%s" % c.get_port(), url="http://www.lthn",
                                     on_press=self.run_browser, size_hint_x=0.1)
                row.add_widget(bbtn)
            else:
                bbtn = BrowserButton(text="N/A", proxy=0, url="http://www.lthn",
                                     disabled=True, size_hint_x=0.1)
                row.add_widget(bbtn)
            if c.get_gate().is_internal():
                dbtn = DisconnectButton(text="N/A ", connection=c, size_hint_x=0.2)
                row.add_widget(dbtn)
            else:
                dbtn = DisconnectButton(text="Disconnect ", on_press=self.disconnect, connection=c, size_hint_x=0.2)
                row.add_widget(dbtn)
            self.ids.connections_info.add_widget(row)

    def show_connection(self, instance):
        client.gui.GUI.ctrl["selected_space"] = instance.spaceid
        client.gui.GUI.ctrl["selected_gate"] = instance.gateid
        self.fill_spaces(selected=instance.spaceid)
        self.fill_gates(selected=instance.gateid)
