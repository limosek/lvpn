import logging
import multiprocessing
import secrets
import socket
import time
from io import StringIO
import paramiko
import sshtunnel
import urllib3

from client.connection import Connection, Connections
from client.tlsproxy import TLSProxy
from lib.mngrrpc import ManagerRpcCall
from lib.service import Service
from lib.session import Session
from lib.shared import Messages


class SSHProxy(Service):

    myname = "sshproxy"

    @classmethod
    def postinit(cls):
        cls.exit = False
        local_addresses = []
        remote_addresses = []
        messages = []
        gate = cls.kwargs["gate"]
        space = cls.kwargs["space"]
        sessionid = cls.kwargs["sessionid"]
        session = cls.ctrl["cfg"].sessions.get(sessionid)
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
                sessions = cls.ctrl["cfg"].sessions.find(gateid=gobj.get_id(), spaceid=space.get_id(), active=True)
                if len(sessions) > 0:
                    nsession = sessions[0]
                else:
                    mr = ManagerRpcCall(space.get_manager_url())
                    try:
                        nsession = Session(cls.ctrl["cfg"], mr.create_session(gobj.get_id(), space.get_id(), session.days_left() + 1))
                        nsession.set_parent(session.get_id())
                        nsession.save()
                    except Exception as e:
                        cls.log_error(e)
                gobj.set_name(gate.get_name() + "/" + gobj.get_name())
                if gobj.is_tls():
                    lport = cls.find_free_port()
                    gobj.set_endpoint("127.0.0.1", lport)
                    gobj.set_name("%s/%s" % (gate.get_name(), gobj.get_name()))
                    connection = Connection(cls.ctrl["cfg"], nsession, port=lport, data={
                        "endpoint": gobj.get_endpoint()
                    }, parent=connectionid)
                    messages.append(
                        Messages.connected_info(connection.get_dict())
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
                            "pid": multiprocessing.current_process().pid
                        }, parent=connectionid)
                        messages.append(
                            Messages.connected_info(connection)
                        )
                local_addresses.append((cls.ctrl["cfg"].local_bind, lport))
                remote_addresses.append((rhost, int(rport)))
                cls.log_info("Create port forward request %s:%s -> %s:%s" % (cls.ctrl["cfg"].local_bind, lport, rhost, rport))
            else:
                cls.log_error("Non-existent SSH gateway %s" % g)
                messages.append(
                    Messages.gui_popup("Non-existent SSH gateway %s" % g)
                )
        cls.log_info("Connecting to SSH proxy %s:%s" % (gate["ssh"]["host"], gate["ssh"]["port"]))
        hostkey = paramiko.pkey.PKey(data=gate["ssh"]["ecdsa-server-public-key"])
        userkey = paramiko.Ed25519Key.from_private_key(StringIO(gate["ssh"]["client-private-key"]))
        tunnel = sshtunnel.SSHTunnelForwarder(
            ssh_username=gate["ssh"]["username"],
            ssh_address_or_host=gate["ssh"]["host"],
            ssh_port=gate["ssh"]["port"],
            #ssh_host_key=hostkey,
            ssh_pkey=userkey,
            local_bind_addresses=local_addresses,
            remote_bind_addresses=remote_addresses)
        try:
            tunnel.logger.setLevel(cls.ctrl["cfg"].l)
            tunnel.start()
        except Exception as e:
            cls.log_error(e)
        for m in messages:
            cls.queue.put(m)
        while tunnel.is_alive and not cls.exit:
            cls.log_debug("%s loop" % cls.myname)
            time.sleep(1)
