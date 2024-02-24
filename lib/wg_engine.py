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
    def replace_macros(cls, txt, iface="", af="", ip="", mask="", prefixlen="", fname=""):
        return txt.replace(
            "{iface}", iface
        ).replace(
            "{af}", af
        ).replace(
            "{ip}", ip
        ).replace(
            "{mask}", mask
        ).replace(
            "{prefixlen}", prefixlen
        ).replace(
            "{fname}", fname
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
                    return name
            except Exception as e:
                raise ServiceException(3, "Bad mapping for --wg-device-map")
        return hashlib.sha1(gateid.encode("utf-8")).hexdigest()[:8]

    @classmethod
    def save_key(cls, key: str):
        tmpfile = tempfile.mktemp("key", "wg", Registry.cfg.tmp_dir)
        with open(tmpfile, "w") as f:
            f.write(key)
        Util.set_key_permissions(tmpfile)
        return os.path.realpath(tmpfile)

    @classmethod
    def set_interface_ip(cls, iface: str, ip: ipaddress.ip_address, ipnet: ipaddress.ip_network):
        if Registry.cfg.wg_cmd_set_ip:
            cls.wg_run_cmd(
                *shlex.split(cls.replace_macros(
                    Registry.cfg.wg_cmd_set_ip, iface=iface, ip=str(ip), mask=str(ipnet.netmask), prefixlen=str(ipnet.prefixlen)
                )))
        else:
            cls.log_error("Cannot create WG interface - missing wg_cmd_create_interface")
            raise ServiceException(3, "Cannot create WG interface - missing wg_cmd_create_interface")

    @classmethod
    def create_wg_interface(cls, name: str, private, port, ip: ipaddress.ip_address, ipnet: ipaddress.ip_network):
        if platform.system() == "Windows":
            tunnelcfg="""
[Interface]
PrivateKey = {key}
ListenPort = {port}
Address = {ip}/{bits}
            """.format(key=private, port=port, ip=str(ip), bits=ipnet.prefixlen)
            fname = os.path.realpath(Registry.cfg.tmp_dir + "/%s.conf" % name)
            with open(fname, "w") as f:
                f.write(tunnelcfg)
            if Registry.cfg.wg_cmd_create_interface:
                cls.wg_run_cmd(
                    *shlex.split(cls.replace_macros(
                        Registry.cfg.wg_cmd_create_interface, fname=fname
                    )))
                time.sleep(4)
            else:
                cls.log_error("Cannot create WG interface - missing wg_cmd_create_interface")
                raise ServiceException(3, "Cannot create WG interface - missing wg_cmd_create_interface")
        else:
            if Registry.cfg.wg_cmd_create_interface:
                wgargs = shlex.split(
                    cls.replace_macros(
                        Registry.cfg.wg_cmd_create_interface, iface=name
                    ))
                try:
                    cls.wg_run_cmd(*wgargs)
                    setargs = [
                        "wg",
                        "set",
                        name,
                        "listen-port", str(port),
                        "private-key", cls.save_key(private)
                    ]
                    cls.wg_run_cmd(*setargs)
                    ipargs = shlex.split(
                        cls.replace_macros(
                            Registry.cfg.wg_cmd_set_ip, iface=name, ip=str(ip), mask=str(ipnet.netmask)
                        ))
                    cls.wg_run_cmd(*ipargs)
                except Exception as e:
                    raise ServiceException(2, str(e))
            else:
                cls.log_error("Cannot create WG interface - missing wg_cmd_create_interface")
                raise ServiceException(3, "Cannot create WG interface - missing wg_cmd_create_interface")

    @classmethod
    def delete_wg_interface(cls, name: str):
        if Registry.cfg.wg_cmd_delete_interface:
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
            cls.log_error("Cannot create WG interface - missing wg_cmd_delete_interface")
            raise ServiceException(3, "Cannot create WG interface - missing wg_cmd_delete_interface")

    @classmethod
    def gather_wg_data(cls, iname: str):
        def replace_none(txt):
            if txt == "(none)":
                return None
            else:
                return txt

        if Registry.cfg.enable_wg:
            output = cls.wg_run_cmd("wg", "show", iname, "dump")
            lines = output.split("\n")
            peers = []
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
                        peer = {
                            "public": fields[0],
                            "preshared": replace_none(fields[1]),
                            "endpoint": replace_none(fields[2]),
                            "allowed_ips": replace_none(fields[3]),
                            "latest_handshake": replace_none(fields[4]),
                            "transfer_rx": replace_none(fields[5]),
                            "transfer_tx": replace_none(fields[6]),
                            "keepalive": replace_none(fields[7])
                        }
                        peers.append(peer)
                    elif len(fields) == 1:
                        pass
                    else:
                        raise ServiceException(4, "Bad wg command output: %s" % output)
                return {
                    "iface": iface,
                    "peers": peers
                }
            else:
                raise ServiceException(4, "Bad wg command output: %s" % output)
        else:
            (private, public) = cls.generate_keys()
            return {
                "iface": {"public": public,
                          "private": private,
                          "port": 0},
                "peers": []
            }

    @classmethod
    def add_peer(cls, iname: str, public: str, allowed_ips: list, endpoint: str = None, preshared: str = None, keepalive: int = 120, show_only: bool = False):
        if endpoint == "dynamic":
            endpoint = None
        ips = ",".join(allowed_ips)
        args = [
            "wg",
            "set",
            iname,
            "peer",
            public,
            "allowed-ips", ips,
            "persistent-keepalive", str(keepalive)
        ]
        if endpoint:
            args.extend(["endpoint", endpoint])
        if preshared:
            args.extend(["preshared-key", cls.save_key(preshared)])
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
        return cls.wg_run_cmd(*args, show_only=show_only)

    @classmethod
    def loop(cls):
        """We do not loop, this is only engine"""
        return
