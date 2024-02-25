import ipaddress

from lib.registry import Registry
from lib.service import ServiceException
from lib.session import Session
from lib.util import Util
from lib.wg_engine import WGEngine
import lib


class WGServerService(lib.wg_service.WGService):

    myname = "wg_server"

    @classmethod
    def postinit(cls):
        if not Registry.cfg.enable_wg:
            WGEngine.show_cmds = True
            WGEngine.show_only = True
        cls.gate = cls.kwargs["gate"]
        cls.setup_interface_server(cls.gate)

    @classmethod
    def loop1(cls):
        if not cls.sactive and cls.session.is_active():
            cls.activate_on_server(cls.session)
            cls.sactive = True

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
            "client_ipv4_address": cls.find_free_ip(session.get_gate()),
            "server_ipv4_address": session.get_gate().get_gate_data("wg")["ipv4_gateway"],
            "server_ipv4_networks": session.get_space()["ips"],
            "ipv4_prefix": ipnet.prefixlen,
            "dns": session.get_space()["dns_servers"]
        }
        session.set_gate_data("wg", data)

    @classmethod
    def activate_on_server(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.add_peer(ifname,
                                 session.get_gate_data("wg")["client_public_key"],
                                [session.get_gate_data("wg")["client_ipv4_address"]],
                                 session.get_gate_data("wg")["client_endpoint"],
                                 session.get_gate_data("wg")["psk"], show_only=show_only)

    @classmethod
    def deactivate_on_server(cls, session, show_only=False):
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.remove_peer(ifname,
                                    session.get_gate_data("wg")["client_public_key"],
                                    show_only=show_only)

    @classmethod
    def find_free_ip(cls, gate):
        gather = WGEngine.gather_wg_data(
            WGEngine.get_interface_name(gate.get_id())
        )
        found_ips = []
        gwnet = ipaddress.ip_network(gate.get_gate_data("wg")["ipv4_network"])
        gw = ipaddress.ip_address(gate.get_gate_data("wg")["ipv4_gateway"])
        for p in gather["peers"]:
            for ip in p["allowed_ips"].split(","):
                ipa = ipaddress.ip_network(ip)
                if ipa.prefixlen == 32:
                    ipa = ipaddress.ip_address(ipa.network_address)
                    if ipa in gwnet:
                        found_ips.append(str(ipa))
                else:
                    continue
        for ip in gwnet:
            if ip == gw or ip == gwnet.network_address or ip == gwnet.broadcast_address:
                continue
            elif str(ip) in found_ips:
                continue
            else:
                return str(ip)

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
                port)
            WGEngine.set_wg_interface_ip(cls.iface,
                ip=ipaddress.ip_address(gate.get_gate_data("wg")["ipv4_gateway"]),
                ipnet=ipaddress.ip_network(gate.get_gate_data("wg")["ipv4_network"]))
        except ServiceException as s:
            try:
                WGEngine.gather_wg_data(cls.iface)
            except ServiceException as s2:
                raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
            pass
