import ipaddress
import multiprocessing
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
        if cls.exit or Registry.cfg.connect_and_exit:
            return
        cls.sactive = False
        while not cls.exit:
            if not cls.sactive and cls.session.is_active():
                cls.activate_on_client(cls.session)
                cls.sactive = True
            time.sleep(1)
        if Registry.cfg.wg_shutdown_on_disconnect:
            cls.log_error("Exiting loop and removing peer")
            cls.deactivate_on_client(cls.session)

    @classmethod
    def postinit(cls):
        if not Registry.cfg.enable_wg:
            raise ServiceException(4, "WG not enabled")
        sessions = Sessions()
        cls.session = cls.kwargs["session"]
        cls.gate = cls.kwargs["gate"]
        cls.space = cls.kwargs["space"]
        cls.iface = WGEngine.get_interface_name(cls.gate.get_id())
        cls.log_warning("WG connect: %s" % cls.session.get_id())
        try:
            # Let us try if interface already exists
            data = WGEngine.gather_wg_data(cls.iface)
            if data["iface"]:
                cls.setup_interface_client(cls.session)
            else:
                cls.deactivate_interface_client()
                cls.setup_interface_client(cls.session)
        except ServiceException as e:
            # It does not exists, let us create
            cls.setup_interface_client(cls.session)
        cls.gathered = WGEngine.gather_wg_data(cls.iface)

        if not cls.session.get_gate_data("wg") or \
                cls.gathered["iface"]["public"] != cls.session.get_gate_data("wg")["client_public_key"]:
            # We are either missing WG session data or WG interface changed keys. So we need to request new session.
            mr = lib.mngrrpc.ManagerRpcCall(cls.gate.get_manager_url())
            rekey = mr.rekey_session(cls.session, cls.gathered["iface"]["public"])
            if not rekey:
                cls.session.remove(deactivate=False)
                session = mr.create_session(cls.session.get_gate(), cls.session.get_space(), cls.session.days(),
                                            prepare_data={"wg": cls.prepare_session_request()})
                if not session:
                    raise ServiceException(33, "Error requesting WG session")
                else:
                    cls.session = Session(session)
                    cls.session.save()
            else:
                cls.session = Session(rekey)
                cls.session.save()

        messages = []
        for g in cls.gate["gates"]:
            gate = Registry.vdp.get_gate(g)
            if gate:
                fresh = sessions.find(gateid=gate.get_id(), spaceid=cls.space.get_id(), active=True, free=True)
                if len(fresh) > 0:
                    for s in fresh:
                        s.remove()
                mr = lib.ManagerRpcCall(cls.space.get_manager_url())
                if cls.space.get_price() == 0 and gate.get_price() == 0:
                    days = Registry.cfg.free_session_days
                else:
                    days = Registry.cfg.auto_pay_days
                session = Session(mr.create_session(gate, cls.space, days))
                session.set_parent(cls.session.get_id())
                session.save()
                messages.append(Messages.connect(session))
            else:
                cls.log_error("Non-existent WG gateway %s" % g)
                messages.append(
                    Messages.gui_popup("Non-existent WG gateway %s" % g)
                )
        for m in messages:
            cls.queue.put(m)

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

            except ServiceException as s:
                try:
                    WGEngine.gather_wg_data(cls.iface)
                except ServiceException as s2:
                    raise ServiceException(4, "Cannot create WG tunnel interface: %s" % s)
                pass
        return True

    @classmethod
    def deactivate_interface_client(cls):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring activation")
            return False
        WGEngine.delete_wg_interface(cls.iface)
        return True

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
            if "client_ipv4_address" in session.get_gate_data("wg"):
                WGEngine.set_interface_ip(ifname,
                                          ipaddress.ip_address(session.get_gate_data("wg")["client_ipv4_address"]),
                                          ipaddress.ip_network(session.get_gate()["wg"]["ipv4_network"]), unset=True)
            if "client_ipv6_address" in session.get_gate_data("wg"):
                WGEngine.set_interface_ip(ifname,
                                          ipaddress.ip_address(session.get_gate_data("wg")["client_ipv6_address"]),
                                          ipaddress.ip_network(session.get_gate()["wg"]["ipv6_network"]), unset=False)

        except ServiceException as e:
            cls.log_error("Error assigning IP: %s" % str(e))
        WGEngine.set_interface_up(ifname)
        nets = []
        if "ipv4_network" in session.get_gate()["wg"]:
            nets.append(ipaddress.ip_network(session.get_gate()["wg"]["ipv4_network"]))
        if "ipv6_network" in session.get_gate()["wg"]:
            nets.append(ipaddress.ip_network(session.get_gate()["wg"]["ipv6_network"]))
        for ipnet in session.get_space()["ipv4_networks"]:
            nets.append(ipnet)
            try:
                WGEngine.add_route(ifname, ipnet, session.get_gate().get_gate_data("wg")["ipv4_gateway"])
            except ServiceException as e:
                cls.log_error("Error adding route: %s" % str(e))
        for ipnet in session.get_space()["ipv6_networks"]:
            nets.append(ipnet)
            try:
                WGEngine.add_route(ifname, ipnet, session.get_gate().get_gate_data("wg")["ipv6_gateway"])
            except ServiceException as e:
                cls.log_error("Error adding route: %s" % str(e))
        if "psk" in session.get_gate_data("wg"):
            psk = session.get_gate_data("wg")
        else:
            psk = None
        WGEngine.add_peer(ifname,
                                 session.get_gate().get_gate_data("wg")["public_key"],
                                 nets,
                                 session.get_gate().get_gate_data("wg")["endpoint"],
                                 psk, keepalive=55, show_only=show_only)
        return True

    @classmethod
    def deactivate_on_client(cls, session, show_only=False):
        if not Registry.cfg.enable_wg:
            cls.log_error("Wireguard not enabled. Ignoring deactivation")
        ifname = WGEngine.get_interface_name(session.get_gate().get_id())
        WGEngine.remove_peer(ifname,
                                    session.get_gate().get_gate_data("wg")["public_key"],
                                    show_only=show_only)
        return True

