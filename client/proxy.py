import copy
import multiprocessing
import os
import secrets
import signal
import logging
import socket
import sys
import time
import _queue

from client.connection import Connection, Connections
from client.sshproxy import SSHProxy
from client.tlsproxy import TLSProxy
from lib.runcmd import RunCmd
from lib.service import Service
from lib.shared import Messages
from lib.util import Util


class ProxyException(Exception):
    pass


class Proxy(Service):
    myname = "proxy"
    processes = []

    @classmethod
    def run(cls, ctrl, queue, myqueue, **kwargs):
        cls.ctrl = ctrl
        cls.queue = queue
        cls.myqueue = myqueue
        cls.processes = []
        cls.ctrl["connections"] = []
        logging.basicConfig(level=ctrl["cfg"].l)
        RunCmd.init(cls.ctrl["cfg"])
        super().run(ctrl, queue, myqueue)

    @classmethod
    def run_tls_proxy(cls, port, session):
        connection = Connection(cls.ctrl["cfg"], session, port=port)
        mp = multiprocessing.Process(target=TLSProxy.run, args=[cls.ctrl, cls.queue, None], kwargs={
            "endpoint": session.get_gate().get_endpoint(resolve=True),
            "ca": session.get_gate().get_ca(),
            "port": port,
            "sessionid": session.get_id(),
            "connectionid": connection.get_id()
        })
        mp.start()
        connection.set_data({
                "endpoint": session.get_gate().get_endpoint(),
                "ca": session.get_gate().get_ca(),
                "pid": mp.pid
            }
        )
        conns = cls.get_value("connections")
        conns.append(connection)
        cls.set_value("connections", conns)
        cls.processes.append(
            {
                "process": mp,
                "session": session,
                "connection": connection
            }
        )

    @classmethod
    def connect(cls, sessionid):
        session = cls.ctrl["cfg"].sessions.get(sessionid)
        if not session:
            raise ProxyException("Unknown sessionid")
        else:
            gateid = session.get_gateid()
            spaceid = session.get_spaceid()
            connections = Connections(cls.ctrl["connections"])
            if connections.is_connected(gateid, spaceid):
                cls.log_warning("Connection to %s/%s is already active." % (gateid, spaceid))
                return True
            gate = cls.ctrl["cfg"].vdp.get_gate(gateid)
            space = cls.ctrl["cfg"].vdp.get_space(spaceid)
        if not gate.is_for_space(space.get_id()):
            raise ProxyException("proxy", "Gate %s is not allowed to connect to space %s" % (gate, space))
        if gate.get_type() in ["http-proxy", "daemon-rpc-proxy", "daemon-p2p-proxy", "socks-proxy"]:
            cls.run_tls_proxy(gate.get_local_port(), session)
        elif gate.get_type() == "ssh":
            connection = Connection(cls.ctrl["cfg"], session)
            args = [cls.ctrl, cls.queue, None]
            kwargs = {
                "gate": gate,
                "space": space,
                "sessionid": sessionid,
                "connectionid": connection.get_id()
            }
            mp = multiprocessing.Process(target=SSHProxy.run, args=args, kwargs=kwargs)
            mp.start()
            connection.set_data({
                    "endpoint": session.get_gate().get_endpoint(),
                    "pid": mp.pid
                }
            )
            conns = cls.get_value("connections")
            conns.append(connection)
            cls.set_value("connections", conns)
            p = {
                    "process": mp,
                    "connection": connection
                }
            cls.processes.append(p)
        else:
            cls.log_error("Unknown gate type %s" % gate.get_type())
            cls.log_gui("proxy", "Unknown gate type %s" % gate.get_type())

    @classmethod
    def get_connections(cls):
        return Connections(cls.get_value("connections"))

    @classmethod
    def update_connections(cls, connections):
        cls.set_value("connections", connections.get_dict())

    @classmethod
    def is_connected(cls, connectionid):
        return cls.get_connections().get(connectionid)

    @classmethod
    def disconnect(cls, connectionid):
        conns = cls.get_connections()
        for p in cls.processes:
            if p["connection"].get_id() == connectionid:
                c = conns.get(connectionid)
                if c:
                    for sub in c.get_children():
                        cls.disconnect(sub)
                cls.log_gui("proxy", "Disconnecting connectionid %s" % connectionid)
                try:
                    p["process"].kill()
                except AttributeError:
                    # We cannot kill thread yet
                    pass
                conns = cls.get_connections()
                conns.remove(p["connection"].get_id())
                cls.update_connections(conns)
        return False

    @classmethod
    def loop(cls):
        while not cls.exit:
            cls.log_debug("Proxy loop")
            for pinfo in cls.processes.copy():
                if pinfo["process"]:
                    try:
                        if pinfo["process"].poll():
                            cls.log_warning(
                                "Connection %s died with exit code %s" % (pinfo["connection"],
                                                                             pinfo["process"].returncode))
                            cls.log_gui("proxy",
                                            "Connection %s died with exit code %s" % (pinfo["connection"],
                                                                                         pinfo["process"].returncode))
                            cls.processes.remove(pinfo)
                            conns = cls.get_connections()
                            conns.remove(pinfo["connection"].get_id())
                            cls.update_connections(conns)
                            break
                    except AttributeError:
                        if not pinfo["process"].is_alive():
                            cls.log_warning(
                                "Connection %s died" % (pinfo["connection"]))
                            cls.log_gui("proxy",
                                            "Connection %s died" % (pinfo["connection"]))
                            cls.processes.remove(pinfo)
                            conns = cls.get_connections()
                            conns.remove(pinfo["connection"].get_id())
                            cls.update_connections(conns)
                            break

            time.sleep(1)
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get()
                    if not msg:
                        continue
                    if msg == Messages.EXIT:
                        break
                    elif msg.startswith(Messages.CONNECT):
                        session = Messages.get_msg_data(msg)
                        cls.connect(session.get_id())
                    elif msg.startswith(Messages.DISCONNECT):
                        connectionid = Messages.get_msg_data(msg)
                        cls.disconnect(connectionid)
                    elif msg.startswith(Messages.CONNECT_INFO):
                        connection = Connection(cls.ctrl["cfg"], connection=Messages.get_msg_data(msg))
                        p = {
                            "process": False,
                            "connection": connection
                        }
                        conns = cls.get_connections()
                        if connection.get_parent():
                            parent = conns.get(connection.get_parent())
                            if parent:
                                parent.add_children(connection.get_id())
                        conns.add(connection)
                        cls.update_connections(conns)
                        cls.processes.append(p)
                except _queue.Empty:
                    continue

        cls.log_gui("proxy", "Proxy process exited")
        cls.stop()

    @classmethod
    def stop(cls):
        cls.exit = True
        for pinfo in cls.processes:
            try:
                if pinfo["process"] and not pinfo["process"].returncode:
                    cls.log_warning("Killing subprocess with PID %s" % pinfo["process"].pid)
                    os.kill(pinfo["process"].pid, signal.SIGINT)
                    #pinfo["process"].communicate()
            except AttributeError:
                pinfo["process"].kill()
                pinfo["process"].join()
