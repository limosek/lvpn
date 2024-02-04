import codecs


class Util:

    @classmethod
    def check_paymentid(cls, paymentid, check_length=True):
        if check_length:
            if len(paymentid) != 16:
                return False
        try:
            codecs.decode(paymentid, "hex")
            return True
        except Exception as e:
            pass
        return False

    @classmethod
    def check_wallet_address(cls, wallet):
        if len(wallet) != 97:
            return False
        if not wallet.startswith("iz"):
            return False
        return True

    @classmethod
    def shorten_wallet_address(cls, wallet):
        return wallet[:5] + "..." + wallet[-10:]
