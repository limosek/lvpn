import time
from kivy.uix.gridlayout import GridLayout

import client
from lib.shared import Messages
from lib.vdp import VDP


class Wizard(GridLayout):

    def wizard(self):
        print("Running wizard")

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def restore_wallet(self, instance=None, value=None):
        client.gui.GUI.queue.put(Messages.wallet_restore(self.ids.wallet_seed.text))
        time.sleep(2)
        self.main()

    def create_wallet(self, instance=None, value=None):
        client.gui.GUI.queue.put(Messages.CREATE_WALLET)
        time.sleep(2)
        self.main()

    def import_vdp(self, instance=None, value=None):
        vdp = VDP(self.ids.vdp_url.text)
        vdp.save(client.gui.GUI.ctrl["cfg"].gates_dir, client.gui.GUI.ctrl["cfg"].spaces_dir)
