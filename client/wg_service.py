import ipaddress
import time

from lib.messages import Messages
from lib.registry import Registry
from lib.service import ServiceException
from lib.session import Session
from lib.sessions import Sessions
from lib.util import Util
from lib.wg_engine import WGEngine
from lib.wg_service import WGService
import lib


class WGClientService(WGService):

    myname = "wg_client"

    @classmethod
    def loop(cls):
        cls.sactive = False
        while not cls.exit:
            if not cls.sactive and cls.session.is_active():
                cls.activate_on_client(cls.session)
                cls.sactive = True
            time.sleep(1)
        cls.deactivate_on_client(cls.session)

    @classmethod
    def postinit(cls):
        if not Registry.cfg.enable_wg:
            WGEngine.show_cmds = True
            WGEngine.show_only = True
        sessions = Sessions(noload=True)
        cls.session = sessions.get(cls.kwargs["sessionid"])
        if cls.session:
            cls.setup_interface_client(cls.session)
        else:
            raise ServiceException(5, "Missing session!")

    @classmethod
    def setup_interface_client(cls, session):
        gate = session.get_gate()
        cls.iface = WGEngine.get_interface_name(gate.get_id())
        port = Util.find_free_port(af="udp")
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard disabled! Returning fake connection")
            cls.log_gui("wg", "Wireguard disabled! Returning fake connection")
        else:
            try:
                WGEngine.gather_wg_data(cls.iface)
            except ServiceException as e:
                try:
                    WGEngine.create_wg_interface(
                        cls.iface,
                        WGEngine.get_private_key(cls.iface),
                        port)
                    if session.get_gate_data("wg") and "client_ipv4_address" in session.get_gate_data("wg"):
                        WGEngine.set_wg_interface_ip(cls.iface,
                                            ip=ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"]),
                                            ipnet=ipaddress.ip_network(gate.get_gate_data("wg")["ipv4_network"]))
                    ifs = cls.get_value("wg_interfaces")
                    ifs.append(cls.iface)
                    cls.set_value("wg_interfaces", list(set(ifs)))
                except ServiceException as s:
                    try:
                        WGEngine.gather_wg_data(cls.iface)
                    except ServiceException as s2:
                        raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
                    pass

    @classmethod
    def deactivate_interface_client(cls):
        WGEngine.delete_wg_interface(cls.iface)

    @classmethod
    def prepare_session_request(cls, session: Session):
        iname = WGEngine.get_interface_name(session.get_gate().get_id())
        cls.setup_interface_client(session)
        gathered = WGEngine.gather_wg_data(iname)
        if gathered:
            data = {
                "endpoint": "dynamic",
                "public_key": gathered["iface"]["public"]
            }
        else:
            raise ServiceException(4, "Cannot gather wg interface data")
        return data

    @classmethod
    def activate_on_client(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        WGEngine.set_interface_ip(ifname, ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"]), ipaddress.ip_network(session.get_gate()["wg"]["ipv4_network"]))
        return WGEngine.add_peer(ifname,
                                 session.get_gate_data("wg")["server_public_key"],
                                [session.get_gate()["wg"]["ipv4_network"]],
                                 session.get_gate()["wg"]["endpoint"],
                                 session.get_gate_data("wg")["psk"], show_only=show_only)

    @classmethod
    def deactivate_on_client(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.remove_peer(ifname,
                                    session.get_gate_data("wg")["server_public_key"],
                                    show_only=show_only)

