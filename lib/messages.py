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
    PAID = "All/Paid"
    UNPAID = "All/UnPaid"
    RESTORE_WALLET = "Wallet/RestoreFromSeed"
    CREATE_WALLET = "Wallet/Create"
    WALLET_ERROR = "All/WalletError"
    GUI_POPUP = "GUI/Popup"

    @classmethod
    def connect(cls, sessionid):
        data = pickle.dumps(sessionid)
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.CONNECT, tdata)
        return msg.strip()

    @classmethod
    def disconnect(cls, connectionid):
        data = pickle.dumps(connectionid)
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.DISCONNECT, tdata)
        return msg.strip()

    @classmethod
    def connected_info(cls, connection):
        data = pickle.dumps(connection.get_dict())
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.CONNECT_INFO, tdata)
        return msg.strip()

    @classmethod
    def pay(cls, payments, paymentid):
        data = pickle.dumps([payments, paymentid])
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.PAY, tdata)
        return msg.strip()

    @classmethod
    def paid(cls, msg):
        data = pickle.dumps(msg)
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.PAID, tdata)
        return msg.strip()

    @classmethod
    def unpaid(cls, msg):
        data = pickle.dumps(msg)
        tdata = codecs.encode(data, "base64").decode("utf-8")
        msg = "%s:%s" % (cls.UNPAID, tdata)
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

    @classmethod
    def init_ctrl(cls, ctrl):
        ctrl["log"] = []
        ctrl["daemon_height"] = -1
        ctrl["selected_gate"] = None
        ctrl["selected_space"] = None
        ctrl["connections"] = []
        ctrl["wallet_address"] = ""
        ctrl["payments"] = {}
        ctrl["balance"] = -1
        ctrl["unlocked_balance"] = -1
        ctrl["wallet_height"] = -1
        ctrl["wallet_address"] = ""
        ctrl["wg_interfaces"] = []
