import codecs
import pickle


class Messages:

    FOR_PROXY = "Proxy"
    FOR_GUI = "GUI"
    FOR_MAIN = "Main"
    FOR_WALLET = "Wallet"
    FOR_ALL = "All"
    EXIT = "All/Exit"
    CONNECT = "Proxy/Connect"
    DISCONNECT = "Proxy/Disconnect"
    CONNECT_INFO = "Proxy/InfoConnect"
    PAY = "Wallet/Pay"
    RESTORE_WALLET = "Wallet/RestoreFromSeed"
    CREATE_WALLET = "Wallet/Create"
    WALLET_ERROR = "All/WalletError"
    GUI_POPUP = "GUI/Popup"

    @classmethod
    def connect(cls, space, gate, authid):
        data = pickle.dumps({"space": space, "gate": gate, "authid": authid})
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.CONNECT, tdata)
        return msg.strip()

    @classmethod
    def disconnect(cls, spaceid, gateid):
        data = pickle.dumps({"spaceid": spaceid, "gateid": gateid})
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.DISCONNECT, tdata)
        return msg.strip()

    @classmethod
    def connect_info(cls, space, gate, authid, data):
        data = pickle.dumps({"space": space, "gate": gate, "authid": authid, "data": data})
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.CONNECT_INFO, tdata)
        return msg.strip()

    @classmethod
    def pay(cls, wallet, amount, authid):
        data = pickle.dumps({"wallet": wallet, "amount": amount, "authid": authid})
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.PAY, tdata)
        return msg.strip()

    @classmethod
    def wallet_restore(cls, seed):
        data = pickle.dumps({"seed": seed})
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.RESTORE_WALLET, tdata)
        return msg.strip()

    @classmethod
    def get_msg_data(cls, msg):
        tdata = msg.split(":")[1].encode("utf-8")
        data = codecs.decode(tdata, "base64")
        data = pickle.loads(data)
        return data

    @classmethod
    def gui_popup(cls, msg):
        data = pickle.dumps(msg)
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.GUI_POPUP, tdata)
        return msg.strip()

    @classmethod
    def is_for_main(cls, msg):
        return msg.startswith(cls.FOR_MAIN)

    @classmethod
    def is_for_all(cls, msg):
        return msg.startswith(cls.FOR_ALL)

    @classmethod
    def is_for_proxy(cls, msg):
        return msg.startswith(cls.FOR_PROXY)

    @classmethod
    def is_for_gui(cls, msg):
        return msg.startswith(cls.FOR_GUI)

    @classmethod
    def is_for_wallet(cls, msg):
        return msg.startswith(cls.FOR_WALLET)
