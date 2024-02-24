import ipaddress
import time

from lib.gate import Gateway
from lib.registry import Registry
from lib.service import Service, ServiceException
from lib.session import Session
from lib.sessions import Sessions
from lib.util import Util
from lib.wg_engine import WGEngine


class WGService(Service):
    myname = "wg_service"

    @classmethod
    def postinit(cls):
        if not Registry.cfg.enable_wg:
            WGEngine.show_cmds = True
            WGEngine.show_only = True
        if Registry.cfg.is_server:
            cls.gate = cls.kwargs["gate"]
            cls.setup_interface_server(cls.gate)
        else:
            sessions = Sessions(noload=True)
            cls.session = sessions.get(cls.kwargs["sessionid"])
            if cls.session:
                cls.setup_interface_client(cls.session)
            else:
                raise ServiceException(5, "Missing session!")

    @classmethod
    def setup_interface_server(cls, gate):
        cls.iface = WGEngine.get_interface_name(gate.get_id())
        try:
            endpoint = gate.get_gate_data("wg")["endpoint"]
            (host, port) = endpoint.split(":")
            port = int(port)
        except Exception as e:
            port = Util.find_free_port(af="udp")
        try:
            WGEngine.create_wg_interface(
                cls.iface,
                WGEngine.generate_keys()[0],
                port,
                ip=ipaddress.ip_address(gate.get_gate_data("wg")["ipv4_gateway"]),
                ipnet=ipaddress.ip_network(gate.get_gate_data("wg")["ipv4_network"])
            )
        except ServiceException as s:
            try:
                WGEngine.gather_wg_data(cls.iface)
            except ServiceException as s2:
                raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
            pass

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
                        WGEngine.generate_keys()[0],
                        port,
                        ip=ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"]),
                        ipnet=ipaddress.ip_network(gate.get_gate_data("wg")["ipv4_network"])
                    )
                except ServiceException as s:
                    try:
                        WGEngine.gather_wg_data(cls.iface)
                    except ServiceException as s2:
                        raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
                    pass

    @classmethod
    def get_free_ip(cls, gate: Gateway):
        gather = WGEngine.gather_wg_data(
            WGEngine.get_interface_name(gate.get_id())
        )
        found_ips = []
        for p in gather["peers"]:
            found_ips += p["allowed_ips"]
        return "192.168.1.100"

    @classmethod
    def prepare_server_session(cls, session: Session, wg_data: dict):
        if "endpoint" in wg_data:
            if wg_data["endpoint"] == "dynamic":
                client_endpoint = "dynamic"
            else:
                client_endpoint = wg_data["endpoint"]
        else:
            client_endpoint = "dynamic"
        ipnet = ipaddress.ip_network(session.get_gate().get_gate_data("wg")["ipv4_network"])
        data = {
            "client_public_key": wg_data["public_key"],
            "client_endpoint": client_endpoint,
            "server_public_key": session.get_gate().get_gate_data("wg")["public_key"],
            "psk": WGEngine.generate_psk(),
            "client_ipv4_address": cls.get_free_ip(session.get_gate()),
            "server_ipv4_address": session.get_gate().get_gate_data("wg")["ipv4_gateway"],
            "server_ipv4_networks": session.get_space()["ips"],
            "ipv4_prefix": ipnet.prefixlen,
            "dns": session.get_space()["dns_servers"]
        }
        session.set_gate_data("wg", data)

    @classmethod
    def prepare_session_request(cls, gate: Gateway):
        iname = WGEngine.get_interface_name(gate.get_id())
        gathered = WGEngine.gather_wg_data(iname)
        if gathered:
            data = {
                "endpoint": "dynamic",
                "public_key": gathered["iface"]["public"]
            }
        else:
            data = None
        return data

    @classmethod
    def activate_on_server(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.add_peer(ifname,
                                 session.get_gate_data("wg")["client_public_key"],
                                [session.get_gate_data("wg")["client_ipv4_address"]],
                                 session.get_gate_data("wg")["client_endpoint"],
                                 session.get_gate_data("wg")["psk"], show_only=show_only)

    @classmethod
    def activate_on_client(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.add_peer(ifname,
                                 session.get_gate_data("wg")["server_public_key"],
                                [session.get_gate()["wg"]["ipv4_network"]],
                                 session.get_gate()["wg"]["endpoint"],
                                 session.get_gate_data("wg")["psk"], show_only=show_only)

    @classmethod
    def deactivate_on_server(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.remove_peer(ifname,
                                    session.get_gate_data("wg")["client_public_key"],
                                    show_only=show_only)

    @classmethod
    def deactivate_on_client(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.remove_peer(ifname,
                                    session.get_gate_data("wg")["server_public_key"],
                                    show_only=show_only)

    @classmethod
    def loop(cls):
        while not cls.exit:
            cls.log_debug("Loop")
            active = WGEngine.gather_wg_data(cls.iface)
            for peer in active["peers"]:
                print(peer)
            time.sleep(20)
        
