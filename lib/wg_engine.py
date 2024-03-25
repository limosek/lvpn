import ipaddress
import logging
import os
import platform
import tempfile
import time
import shlex
import hashlib

from lib.registry import Registry
from lib.runcmd import RunCmd
from lib.service import Service, ServiceException
from lib.util import Util


class WGEngine(Service):
    """Engine - low level utils for Wireguard"""

    myname = "wg_engine"
    show_only = False
    show_cmds = False

    @classmethod
    def wg_run_cmd(cls, *args, input=None, show_only: bool = False):
        if Registry.cfg.wg_cmd_prefix:
            wgargs = Registry.cfg.wg_cmd_prefix.split(" ")
        else:
            wgargs = []
        wgargs.extend(args)
        try:
            if cls.show_cmds:
                if input:
                    cls.log_error("%s | %s" % (input, " ".join(wgargs)))
                else:
                    cls.log_error(" ".join(wgargs))
            if cls.show_only or show_only:
                if input:
                    return "%s | %s" % (input, " ".join(wgargs))
                else:
                    return " ".join(wgargs)
            else:
                ret = RunCmd.get_output(wgargs, input=input)
                return ret
        except Exception as e:
            logging.error(" ".join(wgargs))
            raise ServiceException(2, str(e))

    @classmethod
    def replace_macros(cls, txt: str, **kwargs):
        return txt.format(
            **kwargs
        )

    @classmethod
    def generate_keys(cls):
        private = cls.wg_run_cmd("wg", "genkey").strip()
        public = cls.wg_run_cmd("wg", "pubkey", input=private).strip()
        if cls.show_only or not Registry.cfg.enable_wg:
            return ["Wg-not-enabled-Private", "Wg-not-enabled-Public"]
        else:
            return [private, public]

    @classmethod
    def generate_psk(cls):
        psk = cls.wg_run_cmd("wg", "genpsk").strip()
        if cls.show_only or not Registry.cfg.enable_wg:
            return "Wg-not-enabled-PSK"
        else:
            return psk

    @classmethod
    def get_interface_name(cls, gateid: str):
        for i in Registry.cfg.wg_map_device:
            try:
                (gid, name) = i.split(",")
                if gateid == gid:
                    cls.log_warning("Using manually configured wg interface name: %s -> %s" % (gateid, name))
                    return name
            except Exception as e:
                raise ServiceException(3, "Bad mapping for --wg-map-name")
        if Registry.cfg.is_client:
            return "lvpnc_" + hashlib.sha1(gateid.encode("utf-8")).hexdigest()[:8]
        else:
            return "lvpns_" + hashlib.sha1(gateid.encode("utf-8")).hexdigest()[:8]

    @classmethod
    def get_private_key(cls, gateid: str):
        for i in Registry.cfg.wg_map_privkey:
            try:
                (gid, key) = i.split(",")
                if gateid == gid:
                    cls.log_warning("Using manually configured wg private key: %s -> %s..." % (gateid, key[:3]))
                    return key
            except Exception as e:
                raise ServiceException(3, "Bad mapping for --wg-map-privkey")
        # No predefined keys - generating
        cls.log_warning("Generating new WG interface key for %s" % gateid)
        return cls.generate_keys()[0]

    @classmethod
    def save_key(cls, key: str):
        tmpfile = tempfile.mktemp("key", "wg", Registry.cfg.tmp_dir)
        with open(tmpfile, "w") as f:
            f.write(key)
        return os.path.realpath(tmpfile)

    @classmethod
    def set_interface_ip(cls, iface: str, ip: ipaddress.ip_address, ipnet: ipaddress.ip_network):
        if type(ip) is ipaddress.IPv4Address:
            af = "ipv4"
            tpe = "static"
        else:
            af = "ipv6"
            tpe = ""
        if Registry.cfg.wg_cmd_unset_ips:
            cls.log_info("Removing IPs from WG interface: dev=%s" % iface)
            cls.wg_run_cmd(
                *shlex.split(cls.replace_macros(
                    Registry.cfg.wg_cmd_unset_ips, iface=iface, af=af, type=tpe
                )))
        if Registry.cfg.wg_cmd_set_ip:
            cls.log_info("Setting WG interface IP: dev=%s,ip=%s,ipnet=%s" % (iface, ip, ipnet))
            cls.wg_run_cmd(
                *shlex.split(cls.replace_macros(
                    Registry.cfg.wg_cmd_set_ip, iface=iface, af=af, ip=str(ip), mask=str(ipnet.netmask), prefix=str(ipnet.prefixlen), type=tpe
                )))
        else:
            cls.log_warning("Not creating WG interface - missing wg_cmd_create_interface")

    @classmethod
    def create_wg_interface(cls, name: str, private, port):
        if platform.system() == "Windows":
            tunnelcfg="""
[Interface]
PrivateKey = {key}
ListenPort = {port}
#Address = none
            """.format(key=private, port=port)
            fname = os.path.realpath(Registry.cfg.tmp_dir + "/%s.conf" % name)
            with open(fname, "w") as f:
                f.write(tunnelcfg)
            if Registry.cfg.wg_cmd_create_interface:
                cls.log_info("Creating WG interface: dev=%s" % (name))
                cls.wg_run_cmd(
                    *shlex.split(cls.replace_macros(
                        Registry.cfg.wg_cmd_create_interface, fname=fname
                    )))
                time.sleep(4)
            else:
                cls.log_error("Not creating WG interface - missing wg_cmd_create_interface")

        else:
            if Registry.cfg.wg_cmd_create_interface:
                cls.log_info("Creating WG interface: dev=%s" % (name))
                wgargs = shlex.split(
                    cls.replace_macros(
                        Registry.cfg.wg_cmd_create_interface, iface=name
                    ))
                try:
                    try:
                        cls.wg_run_cmd(*wgargs)
                    except ServiceException as e:
                        """Assuming that interface already exists"""
                        pass
                    setargs = [
                        "wg",
                        "set",
                        name,
                        "listen-port", str(port),
                        "private-key", cls.save_key(private)
                    ]
                    cls.wg_run_cmd(*setargs)
                    cls.set_interface_up(name)
                except Exception as e:
                    raise ServiceException(2, str(e))
            else:
                cls.log_warning("Not creating WG interface - missing wg_cmd_create_interface")

    @classmethod
    def set_interface_up(cls, name):
        if Registry.cfg.wg_cmd_set_interface_up:
            cls.log_info("Setting WG interface up: dev=%s" % name)
            cls.wg_run_cmd(
                *shlex.split(cls.replace_macros(
                    Registry.cfg.wg_cmd_set_interface_up, iface=name
                )))

    @classmethod
    def delete_wg_interface(cls, name: str):
        if Registry.cfg.wg_cmd_delete_interface:
            cls.log_info("Deleting WG interface: dev=%s" % name)
            wgargs = shlex.split(
                cls.replace_macros(
                    Registry.cfg.wg_cmd_delete_interface, iface=name
                ))
            try:
                ret = cls.wg_run_cmd(*wgargs)
                return ret
            except Exception as e:
                raise ServiceException(2, str(e))
        else:
            cls.log_warning("Not deleting WG interface - missing wg_cmd_delete_interface")

    @classmethod
    def add_route(cls, iface: str, ipnet: ipaddress.ip_network, gw: ipaddress.ip_address):
        ipn = ipaddress.ip_network(ipnet)
        if Registry.cfg.wg_cmd_route:
            cls.log_info("Setting IP route: dev=%s,ipnet=%s,gw=%s" % (iface, ipnet, gw))
            wgargs = shlex.split(
                cls.replace_macros(
                    Registry.cfg.wg_cmd_route, iface=iface, network=str(ipnet), gw=str(gw), mask=str(ipn.netmask), prefix=str(ipn.prefixlen)
                ))
            try:
                ret = cls.wg_run_cmd(*wgargs)
                return ret
            except Exception as e:
                raise ServiceException(2, str(e))
        else:
            cls.log_warning("Not adding route - missing wg_cmd_route")
        if Registry.cfg.is_client:
            if Registry.cfg.wg_cmd_nat:
                cls.log_info("Setting NAT: dev=%s,ipnet=%s,gw=%s" % (iface, ipnet, gw))
                wgargs = shlex.split(
                    cls.replace_macros(
                        Registry.cfg.wg_cmd_nat, iface=iface, network=str(ipnet), gw=str(gw), mask=str(ipn.netmask), prefix=str(ipn.prefixlen)
                    ))
                try:
                    ret = cls.wg_run_cmd(*wgargs)
                    return ret
                except Exception as e:
                    raise ServiceException(2, str(e))
            else:
                cls.log_warning("Not adding NAT rule - missing wg_cmd_nat")

    @classmethod
    def parse_show_dump(cls, dump):
        def replace_none(txt):
            if txt == "(none)":
                return None
            else:
                return txt
        lines = dump.split("\n")
        peers = {}
        iface = None
        if len(lines) > 0:
            fields = lines[0].split("\t")
            if len(fields) == 4:
                """ private-key, public-key, listen-port, fwmark"""
                iface = {
                    "public": fields[1],
                    "private": fields[0],
                    "port": fields[2],
                    "fwmark": fields[3]
                }
            for l in lines[1:]:
                fields = l.split("\t")
                if len(fields) == 8:
                    """public-key, preshared-key, endpoint, allowed-ips, latest-handshake, transfer-rx, transfer-tx, persistent-keepalive."""
                    peers[fields[0]] = {
                        "public": fields[0],
                        "preshared": replace_none(fields[1]),
                        "endpoint": replace_none(fields[2]),
                        "allowed_ips": replace_none(fields[3]),
                        "latest_handshake": replace_none(fields[4]),
                        "transfer_rx": replace_none(fields[5]),
                        "transfer_tx": replace_none(fields[6]),
                        "keepalive": replace_none(fields[7])
                    }
                elif len(fields) == 1:
                    pass
                else:
                    raise ServiceException(4, "Bad wg command output: %s" % dump)
            return {
                "iface": iface,
                "peers": peers
            }

    @classmethod
    def gather_wg_data(cls, iname: str):
        if Registry.cfg.enable_wg and not cls.show_only:
            output = cls.wg_run_cmd("wg", "show", iname, "dump")
            data = cls.parse_show_dump(output)
            return data
        else:
            data = """{private}\t{public}\t52820\toff\n{public2}\t{psk}\t1.2.3.4:52820\t172.16.0.0/12,192.168.0.2/32,192.168.0.3/32,192.168.0.4/32\t1708848641\t20899715969\t14596754656\t300""".format(
                private="private1",
                public="public1",
                public2="public2",
                psk="psk"
            )
            return cls.parse_show_dump(data)

    @classmethod
    def add_peer(cls, iname: str, public: str, allowed_ips: list, endpoint: str = None, preshared: str = None, keepalive: int = None, show_only: bool = False):
        if endpoint == "dynamic":
            endpoint = None
        ips = []
        for i in allowed_ips:
            ips.append(str(i))
        args = [
            "wg",
            "set",
            iname,
            "peer",
            public,
            "allowed-ips", ",".join(ips)
        ]
        if keepalive:
            args.extend(["persistent-keepalive", str(keepalive)])
        if endpoint:
            args.extend(["endpoint", endpoint])
        if preshared:
            args.extend(["preshared-key", cls.save_key(preshared)])
        if Registry.cfg.enable_wg:
            logging.getLogger("audit").debug("Adding peer %s/%s" % (iname, public))
            return cls.wg_run_cmd(*args, show_only=show_only)

    @classmethod
    def remove_peer(cls, iname: str, public: str, show_only: bool = False):
        args = [
            "wg",
            "set",
            iname,
            "peer",
            public,
            "remove"
        ]
        if Registry.cfg.enable_wg:
            logging.getLogger("audit").debug("Removing peer %s/%s" % (iname, public))
            return cls.wg_run_cmd(*args, show_only=show_only)

    @classmethod
    def loop(cls):
        """We do not loop, this is only engine"""
        return
