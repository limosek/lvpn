from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
import logging

import client
from client.gui_connect import BrowserButton, Connect
from lib.mngrrpc import ManagerRpcCall


class Status(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def refresh_values(self, dt):
        try:
            self.ids.balance.text = str(client.gui.GUI.ctrl["balance"])
            self.ids.unlocked_balance.text = str(client.gui.GUI.ctrl["unlocked_balance"])
            self.ids.height.text = str(client.gui.GUI.ctrl["daemon_height"])
            self.ids.log.text = "\n".join(client.gui.GUI.ctrl["log"])
            if client.gui.GUI.ctrl["daemon_height"] > 0  and client.gui.GUI.ctrl["wallet_height"] > 0:
                self.ids.wallet_sync_progress.value = client.gui.GUI.ctrl["wallet_height"] / client.gui.GUI.ctrl["daemon_height"]
                if client.gui.GUI.ctrl["daemon_height"] - 2 > client.gui.GUI.ctrl["wallet_height"] and client.gui.GUI.ctrl["wallet_height"]:
                    self.ids.sync_progress_info.text = "Syncing wallet (%s/%s)\nPlease wait." % (client.gui.GUI.ctrl["wallet_height"], client.gui.GUI.ctrl["daemon_height"])
                    self.ids.sync_progress_info.color = (0.7, 0, 0)
                else:
                    if client.gui.GUI.ctrl["cfg"].vdp.get_provider(
                            "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091"):
                        self.ids.buy_credit.disabled = False
                    self.ids.sync_progress_info.text = "Synced (%s)" % client.gui.GUI.ctrl["wallet_height"]
                    self.ids.sync_progress_info.color = (0, 0.7, 0)
            logging.getLogger("gui").debug("Refreshed GUI Status info")
        except ReferenceError:
            pass

    def buy_credit(self):
        provider = client.gui.GUI.ctrl["cfg"].vdp.get_provider(
            "94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091")
        if provider:
            try:
                murl = provider.get_manager_url()
                mngr = ManagerRpcCall(murl)
                purl = mngr.get_payment_url(client.gui.GUI.ctrl["wallet_address"], "0000000000000000")
                if purl:
                    b = BrowserButton(text="Run browser", url=purl, proxy=None)
                    Connect.run_browser(b, incognito=False)
                else:
                    client.gui.GUI.log_gui("client", "Cannot get Stripe payment URL. Please try again later.")

            except Exception as e:
                logging.getLogger("gui").error(e)
