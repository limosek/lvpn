import logging

from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton

import client
from lib.mngrrpc import ManagerRpcCall
from lib.shared import Messages


class SpaceButton(ToggleButton):
    def __init__(self, spaceid, **kwargs):
        super().__init__(group='spaces', **kwargs)
        self.spaceid = spaceid


class GateButton(ToggleButton):
    def __init__(self, gateid, **kwargs):
        super().__init__(group='gates', **kwargs)
        self.gateid = gateid


class DisconnectButton(Button):
    def __init__(self, gateid, spaceid, **kwargs):
        super().__init__(**kwargs)
        self.gateid = gateid
        self.spaceid = spaceid


class PayButton(Button):
    def __init__(self, gateid, spaceid, days, **kwargs):
        super().__init__(**kwargs)
        self._spaceid = spaceid
        self._gateid = gateid
        self._days = days


class Connect(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.gate_filter.bind(text=self.fill_gates)
        self.ids.space_filter.bind(text=self.fill_spaces)
        self.ids.connect_button.bind(on_press=self.connect)
        Clock.schedule_interval(self.fill_connections, 1)

    def connect(self, instance):
        logging.getLogger("gui").warning("Connect %s/%s" % (client.gui.GUI.ctrl["selected_gate"], client.gui.GUI.ctrl["selected_space"]))
        client.gui.GUI.queue.put(Messages.connect(client.gui.GUI.ctrl["selected_space"], client.gui.GUI.ctrl["selected_gate"], None))

    def disconnect(self, instance):
        logging.getLogger("gui").warning("Disconnect %s/%s" % (instance.gateid, instance.spaceid))
        client.gui.GUI.queue.put(Messages.disconnect(gateid=instance.gateid, spaceid=instance.spaceid))

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def pay_service(self, instance):
        space = client.gui.GUI.ctrl["cfg"].vdp.get_space(instance._spaceid)
        gate = client.gui.GUI.ctrl["cfg"].vdp.get_gate(instance._gateid)
        try:
            mngr = ManagerRpcCall("http://localhost:8123")
            data = mngr.preconnect(
                {
                    "spaceid": space.get_id(),
                    "gateid": gate.get_id(),
                    "days": instance._days
                })
            print(data)
            paymentid = data["paymentid"]
            client.gui.GUI.ctrl["payments"][paymentid] = data
            self.parent.prepare_pay(data["wallet"], str(data["price"]), data["paymentid"])
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

    def select_gate(self, instance):
        if instance.state == "down":
            client.gui.GUI.ctrl["selected_gate"] = instance.gateid
            self.ids.connect_button.disabled = False
            authids = client.gui.GUI.ctrl["cfg"].authids.find_for_gate(instance.gateid)
            space = client.gui.GUI.ctrl["cfg"].vdp.get_space(client.gui.GUI.ctrl["selected_space"])
            gate = client.gui.GUI.ctrl["cfg"].vdp.get_gate(client.gui.GUI.ctrl["selected_gate"])
            if (space.get_price() + gate.get_price()) == 0 or len(authids) > 0:
                self.ids.pay_1.disabled = True
                self.ids.pay_30.disabled = True
                self.ids.connect_button.disabled = False
                if (space.get_price() + gate.get_price()) == 0:
                    self.ids.payment_state.text = "Free"
                else:
                    self.ids.payment_state.text = "%s days left" % authids[0].days_left()
            else:
                self.ids.pay_buttons.clear_widgets()
                pay_1 = PayButton(text="Pay 1 day", gateid=client.gui.GUI.ctrl["selected_gate"], spaceid=client.gui.GUI.ctrl["selected_space"], days=1, on_press=self.pay_service)
                pay_30 = PayButton(text="Pay 30 days", gateid=client.gui.GUI.ctrl["selected_gate"], spaceid=client.gui.GUI.ctrl["selected_space"], days=30, on_press=self.pay_service)
                self.ids.pay_buttons.add_widget(pay_1)
                self.ids.pay_buttons.add_widget(pay_30)
                self.ids.connect_button.disabled = True
                self.ids.payment_state.text = "Not paid (%.1f/%.1f per day)" % (space.get_price(), gate.get_price())
        else:
            self.ids.connect_button.disabled = True
            self.ids.payment_state.text = "Unknown"

    def fill_gates(self, instance, value):
        self.ids.choose_gate.clear_widgets()
        if client.gui.GUI.ctrl["selected_space"]:
            disabled = False
        else:
            disabled = True
        for g in client.gui.GUI.ctrl["cfg"].vdp.gates(self.ids.gate_filter.text, client.gui.GUI.ctrl["selected_space"]):
            btn = GateButton(text=g.get_name(), on_press=self.select_gate, gateid=g.get_id(), disabled=disabled)
            setattr(self.ids, g.get_id(), btn)
            self.ids.choose_gate.add_widget(btn)

    def fill_spaces(self, instance, value):
        self.ids.choose_space.clear_widgets()
        for s in client.gui.GUI.ctrl["cfg"].vdp.spaces(self.ids.space_filter.text):
            btn = SpaceButton(text=s.get_name(), on_press=self.select_space, spaceid=s.get_id())
            setattr(self.ids, s.get_id(), btn)
            self.ids.choose_space.add_widget(btn)

    def fill_connections(self, dt):
        self.ids.connections_info.clear_widgets()
        for c in client.gui.GUI.ctrl["connections"]:
            btn = DisconnectButton(text="Disconnect " + c["gate"].get_name() + "/" + c["space"].get_name(), on_press=self.disconnect, gateid=c["gate"].get_id(), spaceid=c["space"].get_id())
            self.ids.connections_info.add_widget(btn)
