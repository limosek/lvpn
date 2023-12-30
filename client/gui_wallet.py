import codecs
import logging
import time

from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout

import client
from lib.shared import Messages


class Wallet(GridLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.amount_to_send.bind(text=self.check_validity)
        self.ids.paymentid_to_send.bind(text=self.check_validity)
        self.ids.wallet_to_send.bind(text=self.check_validity)
        Clock.schedule_once(self.check_validity, 1)

    @staticmethod
    def get_tx_uri(wallet, amount, paymentid):
        uri = "lethean:%s?tx_amount=%s,tx_payment_id=%s" % (wallet, amount, paymentid)
        return uri

    @staticmethod
    def get_rx_uri(wallet):
        uri = "lethean_wallet:%s" % wallet
        return uri

    def main(self):
        self.clear_widgets()
        self.add_widget(client.gui_switcher.Switcher())

    def pay(self, instance=None, value=None):
        price = self.ids.amount_to_send.text
        paymentid = self.ids.paymentid_to_send.text
        wallet = self.ids.wallet_to_send.text
        client.gui.GUI.queue.put(Messages.pay(wallet, price, paymentid))
        time.sleep(2)
        self.main()

    def check_validity(self, instance=None, value=None):
        try:
            self.ids.qr_get.data = self.get_rx_uri(client.gui.GUI.ctrl["wallet_address"])
            self.ids.receive_address.text = client.gui.GUI.ctrl["wallet_address"]
            if self.ids.qr_get.data == "None":
                self.ids.qr_get.disabled = True
            else:
                self.ids.qr_get.disabled = False

            try:
                amount = float(self.ids.amount_to_send.text)
            except Exception as e:
                self.ids.pay_button.disabled = True
                self.ids.amount_to_send.background_color = (0.7, 0, 0)
                error = True
                amount = 0

            if len(self.ids.paymentid_to_send.text) == 0:
                perror = False
                error = False
            else:
                if len(self.ids.paymentid_to_send.text) != 16:
                    perror = True
                    error = True
                else:
                    try:
                        codecs.decode(self.ids.paymentid_to_send.text, "hex")
                        error = False
                        perror = False
                    except Exception as e:
                        error = True
                        perror = True
            if perror:
                self.ids.paymentid_to_send.background_color = (0.7, 0, 0)
            else:
                self.ids.paymentid_to_send.background_color = (0, 0.7, 0)

            if len(self.ids.wallet_to_send.text) >= 90 and self.ids.wallet_to_send.text.startswith("iz"):
                self.ids.wallet_to_send.background_color = (0, 0.7, 0)
            else:
                self.ids.wallet_to_send.background_color = (0.7, 0, 0)

            if amount > 0:
                self.ids.amount_to_send.background_color = (0, 0.7, 0)
            else:
                self.ids.amount_to_send.background_color = (0.7, 0, 0)

            if error:
                self.ids.pay_button.disabled = True
                self.ids.qr_send.disabled = False
            else:
                self.ids.pay_button.disabled = False
                self.ids.qr_send.data = self.get_tx_uri(self.ids.wallet_to_send.text, self.ids.amount_to_send.text,
                                                    self.ids.paymentid_to_send.text)
                self.ids.qr_send.disabled = False

        except Exception as e:
            logging.getLogger("gui").error(e)
