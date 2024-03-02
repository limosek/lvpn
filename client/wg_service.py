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
            return False
        sessions = Sessions()
        cls.session = cls.kwargs["session"]
        cls.gate = cls.kwargs["gate"]
        cls.space = cls.kwargs["space"]
        cls.iface = WGEngine.get_interface_name(cls.gate.get_id())
        try:
            cls.deactivate_interface_client()
        except ServiceException as e:
            pass
        cls.setup_interface_client(cls.session)
        cls.gathered = WGEngine.gather_wg_data(cls.iface)
        mr = lib.mngrrpc.ManagerRpcCall(cls.space.get_manager_url())
        nsession = Session(mr.create_session(cls.gate, cls.space,
                              prepare_data={"wg": cls.gate.get_prepare_data()}))
        nsession.save()
        # Let us remove presession and enable session
        sessions.remove(cls.session)
        sessions.add(nsession)
        cls.session = nsession
        cls.queue.put(Messages.connect(nsession))
        for g in cls.gate["gates"]:
            session = Session()
            session.generate(g, cls.space.get_id(), 1)
            session.save()
            cls.queue.put(Messages.connect(session))

    @classmethod
    def setup_interface_client(cls, session):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring activation")
            return False
        gate = session.get_gate()
        port = Util.find_free_port(af="udp")
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard disabled! Returning fake connection")
            cls.log_gui("wg", "Wireguard disabled! Returning fake connection")
        else:
            try:
                WGEngine.create_wg_interface(
                    cls.iface,
                    WGEngine.get_private_key(session.get_gate().get_id()),
                    port)
                if session.get_gate_data("wg"):
                    if "client_ipv4_address" in session.get_gate_data("wg"):
                        WGEngine.set_wg_interface_ip(cls.iface,
                                                     ip=ipaddress.ip_address(
                                                         session.get_gate_data("wg")["client_ipv4_address"]),
                                                     ipnet=ipaddress.ip_network(
                                                         gate.get_gate_data("wg")["ipv4_network"]))
                    if "client_ipv6_address" in session.get_gate_data("wg"):
                        WGEngine.set_wg_interface_ip(cls.iface,
                                                     ip=ipaddress.ip_address(
                                                         session.get_gate_data("wg")["client_ipv6_address"]),
                                                     ipnet=ipaddress.ip_network(
                                                         gate.get_gate_data("wg")["ipv6_network"]))

            except ServiceException as s:
                try:
                    WGEngine.gather_wg_data(cls.iface)
                except ServiceException as s2:
                    raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
                pass

    @classmethod
    def deactivate_interface_client(cls):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring activation")
            return False
        WGEngine.delete_wg_interface(cls.iface)

    @classmethod
    def prepare_session_request(cls):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring activation")
            return False
        gathered = WGEngine.gather_wg_data(cls.iface)
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
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring activation")
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        try:
            if "client_ipv4_address" in ipaddress.ip_address(session.get_gate_data("wg")):
                WGEngine.set_interface_ip(ifname,
                                          ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"]),
                                          ipaddress.ip_network(session.get_gate()["wg"]["ipv4_network"]))
            if "client_ipv6_address" in ipaddress.ip_address(session.get_gate_data("wg")):
                WGEngine.set_interface_ip(ifname,
                                          ipaddress.ip_address(session.get_gate_data("wg")["client_ipv6_address"]),
                                          ipaddress.ip_network(session.get_gate()["wg"]["ipv6_network"]))

        except ServiceException as e:
            cls.log_error("Error assigning IP: %s" % str(e))
        WGEngine.set_interface_up(ifname)
        nets = []
        if "ipv4_network" in session.get_gate()["wg"]:
            nets.append(ipaddress.ip_network(session.get_gate()["wg"]["ipv4_network"]))
        if "ipv6_network" in session.get_gate()["wg"]:
            nets.append(ipaddress.ip_network(session.get_gate()["wg"]["ipv6_network"]))
        for ipnet in session.get_space()["ips"]:
            try:
                nets.append(ipnet)
                if type(ipnet) is ipaddress.IPv4Network:
                    WGEngine.add_route(ifname, ipnet, session.get_gate().get_gate_data("wg")["ipv4_gateway"])
                else:
                    WGEngine.add_route(ifname, ipnet, session.get_gate().get_gate_data("wg")["ipv6_gateway"])
            except ServiceException as e:
                cls.log_error("Error adding route: %s" % str(e))
        return WGEngine.add_peer(ifname,
                                 session.get_gate_data("wg")["server_public_key"],
                                 nets,
                                 session.get_gate()["wg"]["endpoint"],
                                 session.get_gate_data("wg")["psk"], show_only=show_only)

    @classmethod
    def deactivate_on_client(cls, session, show_only=False):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring deactivation")
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        return WGEngine.remove_peer(ifname,
                                    session.get_gate_data("wg")["server_public_key"],
                                    show_only=show_only)

