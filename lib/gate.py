import logging
import os.path
import socket
import time
from ownca import CertificateAuthority
import dns.resolver

import client.wg_service
import server.wg_service
from lib.registry import Registry
from lib.runcmd import RunCmd
from lib.util import Util
from lib.vdpobject import VDPObject, VDPException


class Gateway(VDPObject):

    def __init__(self, gwinfo, file=None, vdp=None):
        if not vdp:
            vdp = Registry.vdp
        self.validate(gwinfo, "Gate", file)
        self._data = gwinfo
        self._provider = vdp.get_provider(self._data["providerid"])
        if not self._provider:
            raise VDPException("Unknown providerid %s" % self._data["providerid"])
        self._local = self._provider.is_local()

    def get_id(self):
        return self.get_provider_id() + "." + self._data["gateid"]

    def get_ca(self):
        if self.get_gate_data(self.get_type()) \
                and "tls" in self.get_gate_data(self.get_type()) \
                and not self.get_gate_data(self.get_type())["tls"]:
            return None
        else:
            if "ca" in self._data:
                return self._data["ca"]
            else:
                return self.get_provider().get_ca()

    def set_provider(self, provider):
        self._provider = provider
        self._local = self._provider.is_local()

    def get_endpoint(self, resolve=False, dnsservers=None):
        if not resolve:
            return "%s:%s" % (self._data[self.get_type()]["host"], self._data[self.get_type()]["port"])
        else:
            try:
                if 0 and self.is_internal():
                    """Internal resolver is disabled for now"""
                    resolver = dns.resolver.Resolver()
                    if dnsservers:
                        resolver.nameservers = dnsservers
                    dns.resolver.override_system_resolver(resolver)
                    answers = dns.resolver.resolve(self._data[self.get_type()]["host"], 'A')
                    if len(answers.rrset) > 0:
                        ip = str(answers.rrset[0])
                    else:
                        return tuple([self._data[self.get_type()]["host"], self._data[self.get_type()]["port"]])
                else:
                    ip = socket.gethostbyname(self._data[self.get_type()]["host"])
                return tuple([ip, self._data[self.get_type()]["port"]])
            except socket.error:
                logging.getLogger("vdp").error("Error resolving %s" % self._data[self.get_type()]["host"])
                return tuple([self._data[self.get_type()]["host"], self._data[self.get_type()]["port"]])
            except dns.resolver.NXDOMAIN:
                logging.getLogger("vdp").error("Error resolving %s" % self._data[self.get_type()]["host"])
                return tuple([self._data[self.get_type()]["host"], self._data[self.get_type()]["port"]])

    def set_endpoint(self, host, port):
        self._data[self.get_type()]["host"] = host
        self._data[self.get_type()]["port"] = port

    def is_for_space(self, spaceid):
        if spaceid in self._data["spaces"]:
            return True
        else:
            return False

    def get_replaces(self):
        if "replaces" in self._data:
            return self._data["replaces"]
        else:
            return False

    def is_tls(self):
        if "tls" in self._data[self.get_type()]:
            if self._data[self.get_type()]["tls"]:
                return True
            else:
                return False
        else:
            return True

    def get_wallet(self):
        return self.get_provider().get_wallet()

    def get_local_port(self):
        if self.get_type() == "http-proxy":
            if Util.test_free_port(8080):
                return 8080
            else:
                return Util.find_free_port()
        elif self.get_type() == "daemon-rpc-proxy":
            if Util.test_free_port(48782):
                return 48782
            else:
                return Util.find_free_port()
        elif self.get_type() == "daemon-p2p-proxy":
            if Util.test_free_port(48772):
                return 48772
            else:
                return Util.find_free_port()
        elif self.get_type() == "socks-proxy":
            if Util.test_free_port(8081):
                return 8081
            else:
                return Util.find_free_port()
        else:
            return None

    def space_ids(self):
        return self._data["spaces"]

    def save(self, cfg=None):
        if cfg:
            Registry.cfg = cfg
        fname = "%s/%s.lgate" % (Registry.cfg.gates_dir, self.get_id())
        with open(fname, "w") as f:
            f.write(self.get_json())

    def get_title(self):
        return self._data["name"]

    def get_gate_data(self, gate):
        if gate in self._data:
            return self._data[gate]
        else:
            return False

    def get_prepare_data(self):
        if self.get_type() == "wg":
            data = client.wg_service.WGClientService.prepare_session_request()
        else:
            data = {}
        return data

    def activate_client(self, session):
        if session.get_gate().get_type() == "wg":
            if session.get_gate_data("wg"):
                client.wg_service.WGClientService.activate_on_client(session)
            else:
                logging.getLogger("audit").warning("Not activating WG session. Missing WG data.")
                return False

    def activate_server(self, session):
        if self.get_type() == "ssh":
            user_key = "%s/user-%s" % (Registry.cfg.tmp_dir, session.get_id())
            user_key_pub = "%s.pub" % user_key
            user_cert = "%s/user-%s-cert.pub" % (Registry.cfg.tmp_dir, session.get_id())
            username = session.get_gate().get_gate_data("ssh")["username"]
            cmd = [
                "ssh-keygen",
                "-f", user_key,
                "-C", "%s-%s" % (username, self.get_id()),
                "-t", "ecdsa",
                "-N", ""
            ]

            if RunCmd.get_output(cmd):
                pass
            else:
                logging.getLogger().error("Error activating session %s" % self.get_id())
            cmd = [
                "ssh-keygen",
                "-s", Registry.cfg.ssh_user_ca_private,
                "-C", "gateid=%s,username=%s,sessionid=%s" % (session.get_gate().get_id(), username, self.get_id()),
                "-I", session.get_id() + "@lvpn",
                "-n", username,
                "-V", "+%sd" % (session.days_left() + 1),
                user_key_pub]
            logging.getLogger().info("Running command %s" % " ".join(cmd))
            if RunCmd.get_output(cmd):
                pass
            else:
                logging.getLogger().error("Error activating session %s" % self.get_id())
            with open(user_cert, "r") as f:
                crt = f.read(10000)
            with open(user_key, "r") as f:
                key = f.read(10000)
            if not session.is_free():
                session.set_gate_data("ssh", {
                    "key": key,
                    "crt": crt,
                    "port": Util.find_random_free_port()
                })
            else:
                session.set_gate_data("ssh", {
                    "key": key,
                    "crt": crt
                })

        elif self.get_type() in ["http-proxy", "socks-proxy", "daemon-rpc-proxy", "daemon-p2p-proxy"] and self.is_tls():
            ca = CertificateAuthority(ca_storage=Registry.cfg.ca_dir)
            lckfile = "%s/lock" % Registry.cfg.ca_dir
            while os.path.exists(lckfile):
                time.sleep(0.1)
            with open(lckfile, "w") as lck:
                lck.write(str(os.getpid()))
            try:
                crt = ca.issue_certificate("%s.lvpn" % session.get_id(), maximum_days=session.days_left() + 1,
                                           key_size=4096)
                session.set_gate_data("proxy", {
                    "key": crt.key_bytes.decode("utf-8"),
                    "crt": crt.cert_bytes.decode("utf-8")
                })
            except Exception as e:
                os.unlink(lckfile)
                return False
            os.unlink(lckfile)

        elif self.get_type() == "wg":
            if session.get_gate_data("wg"):
                server.wg_service.WGServerService.activate_on_server(session)
            else:
                logging.getLogger("audit").warning("Not activating WG session. Missing WG data.")
                return False
        return True

    def deactivate_client(self, session):
        if self.get_type() == "wg":
            client.wg_service.WGClientService.deactivate_on_client(session)

    def deactivate_server(self, session):
        if self.get_type() == "wg":
            server.wg_service.WGServerService.deactivate_on_server(session)

    def __repr__(self):
        if Registry.cfg.is_server:
            return "Gateway %s/%s[local=%s]" % (self._data["gateid"], self._data["name"], self.is_local())
        else:
            return "Gateway %s/%s" % (self._data["gateid"], self._data["name"])
