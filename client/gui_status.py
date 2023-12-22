from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
import logging

import client


class Status(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def refresh_values(self, dt):
        logging.getLogger("gui").info("Refreshing Status info")
        try:
            self.ids.balance.text = str(client.gui.GUI.ctrl["balance"])
            self.ids.unlocked_balance.text = str(client.gui.GUI.ctrl["unlocked_balance"])
            self.ids.height.text = str(client.gui.GUI.ctrl["daemon_height"])
            self.ids.log.text = client.gui.GUI.ctrl["log"]
            if client.gui.GUI.ctrl["daemon_height"] > 0  and client.gui.GUI.ctrl["wallet_height"] > 0:
                self.ids.wallet_sync_progress.value = client.gui.GUI.ctrl["wallet_height"] / client.gui.GUI.ctrl["daemon_height"]
                if client.gui.GUI.ctrl["daemon_height"] - 2 > client.gui.GUI.ctrl["wallet_height"] and client.gui.GUI.ctrl["wallet_height"]:
                    self.ids.sync_progress_info.text = "Syncing wallet (%s/%s)\nPlease wait." % (client.gui.GUI.ctrl["wallet_height"], client.gui.GUI.ctrl["daemon_height"])
                    self.ids.sync_progress_info.color = (0.7, 0, 0)
                else:
                    self.ids.sync_progress_info.text = "Synced (%s)" % client.gui.GUI.ctrl["wallet_height"]
                    self.ids.sync_progress_info.color = (0, 0.7, 0)
        except Exception as e:
            logging.getLogger("gui").error(e)

