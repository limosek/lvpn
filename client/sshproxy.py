import logging
import multiprocessing
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from io import StringIO

import _queue
import paramiko
import sshtunnel
import urllib3

from client.connection import Connection, Connections
from client.tlsproxy import TLSProxy
from lib.mngrrpc import ManagerRpcCall, ManagerException
from lib.runcmd import RunCmd
from lib.service import Service, ServiceException
from lib.session import Session
from lib.sessions import Sessions
from lib.messages import Messages
from lib.util import Util


class SSHProxy(Service):

    myname = "sshproxy"

    @classmethod
    def postinit(cls):
        cls.exit = False
        local_addresses = []
        remote_addresses = []
        redirects = []
        messages = []
        gate = cls.kwargs["gate"]
        space = cls.kwargs["space"]
        sessionid = cls.kwargs["sessionid"]
        cls.sessions = Sessions(cls.ctrl["cfg"])
        session = cls.sessions.get(sessionid)
        connectionid = cls.kwargs["connectionid"]
        logging.getLogger("paramiko").setLevel(cls.ctrl["cfg"].l)
        for g in gate["gates"]:
            gobj = cls.ctrl["cfg"].vdp.get_gate(g)
            if gobj:
                try:
                    (rhost, rport) = gobj.get_endpoint().split(":")
                except Exception as e:
                    cls.log_error(e)
                    continue
                sessions = cls.sessions.find(gateid=gobj.get_id(), spaceid=space.get_id(), active=True)
                if len(sessions) > 0:
                    nsession = sessions[0]
                else:
                    try:
                        mr = ManagerRpcCall(space.get_manager_url())
                        nsession = Session(cls.ctrl["cfg"], mr.create_session(gobj.get_id(), space.get_id(), session.days_left() + 1))
                        nsession.set_parent(session.get_id())
                        nsession.save()
                    except ManagerException as e:
                        cls.log_error("Cannot contact manager at %s: %s" % (space.get_manager_url(), e))
                        cls.log_gui("proxy", "Cannot contact manager at %s: %s" % (space.get_manager_url(),e))
                        raise ServiceException(4, e)
                gobj.set_name(gate.get_name() + "/" + gobj.get_name())
                if gobj.is_tls():
                    lport = Util.find_free_port()
                    gobj.set_endpoint("127.0.0.1", lport)
                    gobj.set_name("%s/%s" % (gate.get_name(), gobj.get_name()))
                    connection = Connection(cls.ctrl["cfg"], nsession, port=lport, data={
                        "endpoint": gobj.get_endpoint(),
                        "gateid": gobj.get_id(),
                        "spaceid": space.get_id()
                    }, parent=connectionid)
                    messages.append(
                        Messages.connected_info(connection)
                    )
                else:
                    lport = gobj.get_local_port()
                    if not lport:
                        cls.log_error("Bad gate to connect via SSH (no local port): %s" % gobj)
                        messages.append(
                            Messages.gui_popup("Bad gate to connect via SSH (no local port): %s" % gobj)
                        )
                        continue
                    else:
                        connection = Connection(cls.ctrl["cfg"], nsession, port=lport, data={
                            "endpoint": gobj.get_endpoint(),
                            "pid": multiprocessing.current_process().pid,
                            "gateid": gobj.get_id(),
                            "spaceid": space.get_id()

                        }, parent=connectionid)
                        messages.append(
                            Messages.connected_info(connection)
                        )
                local_addresses.append((cls.ctrl["cfg"].local_bind, lport))
                remote_addresses.append((rhost, int(rport)))
                redirects.append("-L%s:%s:%s:%s" % (cls.ctrl["cfg"].local_bind, lport, rhost, rport))
                cls.log_info("Create port forward request %s:%s -> %s:%s" % (cls.ctrl["cfg"].local_bind, lport, rhost, rport))
            else:
                cls.log_error("Non-existent SSH gateway %s" % g)
                messages.append(
                    Messages.gui_popup("Non-existent SSH gateway %s" % g)
                )
        cls.log_info("Connecting to SSH proxy %s:%s" % (gate["ssh"]["host"], gate["ssh"]["port"]))
        prepareddata = cls.prepare(session, cls.ctrl["cfg"].tmp_dir, redirects)
        RunCmd.init(cls.ctrl["cfg"])
        if cls.ctrl["cfg"].ssh_engine == "ssh":
            sshargs = prepareddata["sshargs"]
            for m in messages:
                cls.queue.put(m)
            cls.p = RunCmd.popen(sshargs)
            return cls.p
        else:
            cls.tunnel = sshtunnel.SSHTunnelForwarder(
                ssh_username=gate["ssh"]["username"],
                ssh_address_or_host=gate["ssh"]["host"],
                ssh_port=gate["ssh"]["port"],
                ssh_pkey=prepareddata["key"],
                local_bind_addresses=local_addresses,
                remote_bind_addresses=remote_addresses)
            cls.tunnel.logger.setLevel(cls.ctrl["cfg"].l)
            cls.tunnel.start()
            for m in messages:
                cls.queue.put(m)

    @classmethod
    def prepare(cls, session, dir, redirects):
        sshdata = session.get_gate_data("ssh")
        if sshdata:
            gate = session.get_gate()
            keyfile = "%s/ssh_id_%s" % (dir, session.get_id())
            crtfile = "%s/ssh_id_%s-cert.pub" % (dir, session.get_id())
            if os.path.exists(keyfile):
                os.unlink(keyfile)
            with open(keyfile, "w") as f:
                f.write(sshdata["key"])
            with open(crtfile, "w") as f:
                f.write(sshdata["crt"])
            Util.set_key_permissions(keyfile)
            if "port" in sshdata:
                redirects.extend(["-g", "-R0.0.0.0:%s:127.0.0.1:1234" % sshdata["port"]])
            sshargs = [
                "ssh",
                "-i", keyfile,
                "-o", "UserKnownHostsFile=%s/known_hosts" % dir,
                "-o", "StrictHostKeyChecking=accept-new",
                "-p", str(gate["ssh"]["port"]),
                "-T", "-n", "-N"]
            sshargs.extend(redirects)
            sshargs.append("%s@%s" % (gate["ssh"]["username"], gate["ssh"]["host"]))
            return {
                "key": keyfile,
                "crt": crtfile,
                "sshargs": sshargs,
                "sshcmd": " ".join(sshargs)
            }
        else:
            raise ServiceException(2, "Missing SSH data within session")

    @classmethod
    def loop(cls):
        if cls.ctrl["cfg"].ssh_engine == "ssh":
            return
        else:
            while cls.tunnel.is_alive and not cls.exit:
                cls.log_debug("%s loop" % cls.myname)
                time.sleep(1)
