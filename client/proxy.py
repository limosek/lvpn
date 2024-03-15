import multiprocessing
import os
import signal
import logging
import threading
import time
from subprocess import Popen
import _queue

from client.connection import Connection, Connections
from client.sshproxy import SSHProxy
from client.tlsproxy import TLSProxy
from client.wg_service import WGClientService
from lib.registry import Registry
from lib.runcmd import RunCmd, Process
from lib.service import Service, ServiceException
from lib.sessions import Sessions
from lib.messages import Messages
from lib.wg_engine import WGEngine
import lib


class ProxyException(Exception):
    pass


class Proxy(Service):
    myname = "proxy"
    processes = []

    @classmethod
    def run(cls, ctrl, queue, myqueue, **kwargs):
        cls.ctrl = ctrl
        if multiprocessing.parent_process():
            Registry.cfg = ctrl["cfg"]
            Registry.vdp = Registry.cfg.vdp
        cls.queue = queue
        cls.myqueue = myqueue
        cls.processes = []
        cls.ctrl["connections"] = []
        logging.basicConfig(level=Registry.cfg.l)
        super().run(ctrl, queue, myqueue)

    @classmethod
    def run_tls_proxy(cls, port, session):
        connection = Connection(session, port=port)
        mp = Process(target=TLSProxy.run, args=[cls.ctrl, cls.queue, None], kwargs={
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
        cls.processes.append(
            {
                "process": mp,
                "session": session,
                "connection": connection
            }
        )
        return connection

    @classmethod
    def connect(cls, connections, sessionid):
        session = Sessions(noload=True).get(sessionid)
        if not session:
            cls.log_error(ProxyException("Unknown sessionid %s" % sessionid))
            return False
        else:
            gateid = session.get_gateid()
            spaceid = session.get_spaceid()
            if connections.is_connected(gateid, spaceid):
                cls.log_warning("Connection to %s/%s is already active." % (gateid, spaceid))
                return True
            gate = Registry.vdp.get_gate(gateid)
            space = Registry.vdp.get_space(spaceid)
        if not gate.is_for_space(space.get_id()):
            raise ProxyException("proxy", "Gate %s is not allowed to connect to space %s" % (gate, space))
        if gate.get_replaces():
            replaced_connection = connections.find_by_gateid(gate.get_replaces())
            if replaced_connection:
                # If this connection replaces other, let us disconnect old first
                cls.disconnect(connections, replaced_connection)
                time.sleep(1)
        if gate.get_type() in ["http-proxy", "daemon-rpc-proxy", "daemon-p2p-proxy", "socks-proxy"]:
            connection = cls.run_tls_proxy(gate.get_local_port(), session)
            connections.add(connection)
            cls.update_connections(connections)

        elif gate.get_type() == "ssh":
            connection = Connection(session)
            args = [cls.ctrl, cls.queue, None]
            kwargs = {
                "gate": gate,
                "space": space,
                "sessionid": sessionid,
                "connectionid": connection.get_id()
            }
            if Registry.cfg.ssh_engine == "ssh":
                try:
                    SSHProxy.run(*args, **kwargs)
                except ServiceException as s:
                    cls.log_error("Error running ssh proxy %s: %s" % (session.get_id(), s))
                    cls.log_gui("proxy", "Error running ssh proxy %s: %s" % (session.get_id(), s))
                    cls.queue.put(Messages.gui_popup("Error running ssh proxy %s: %s" % (session.get_id(), s)))
                    return False
                p = SSHProxy.p
                if Registry.cfg.connect_and_exit:
                    return
                connection.set_data({
                        "endpoint": session.get_gate().get_endpoint(),
                        "pid": p.pid,
                        "gateid": gate.get_id(),
                        "spaceid": space.get_id()
                    }
                )
                p = {
                    "process": p,
                    "connection": connection
                }
                cls.processes.append(p)
            else:
                mp = Process(target=SSHProxy.run, args=args, kwargs=kwargs)
                mp.start()
                connection.set_data({
                        "endpoint": session.get_gate().get_endpoint(),
                        "pid": mp.pid,
                        "gateid": gate.get_id(),
                        "spaceid": space.get_id()
                    })
                p = {
                    "process": mp,
                    "connection": connection
                }
                cls.processes.append(p)
            connections.add(connection)
            cls.update_connections(connections)

        elif gate.get_type() == "wg":
            connection = Connection(session)
            args = [cls.ctrl, cls.queue, None]
            kwargs = {
                "gate": gate,
                "space": space,
                "sessionid": sessionid,
                "session": session,
                "connectionid": connection.get_id()
            }
            mp = Process(target=WGClientService.run, args=args, kwargs=kwargs)
            mp.start()
            connection.set_data({
                "endpoint": session.get_gate().get_gate_data("wg")["endpoint"],
                "pid": mp.pid,
                "gateid": gate.get_id(),
                "spaceid": space.get_id(),
                "interface": WGEngine.get_interface_name(gate.get_id())
            })
            p = {
                "process": mp,
                "connection": connection
            }
            cls.processes.append(p)
            connections.add(connection)
            cls.update_connections(connections)
            pass

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
    def disconnect(cls, connections, connectionid):
        for p in cls.processes:
            if p["connection"].get_id() == connectionid:
                c = connections.get(connectionid)
                if c:
                    if c.get_gate().get_type() == "wg":
                        WGClientService.deactivate_on_client(c.get_session())
                    for sub in c.get_children():
                        cls.disconnect(connections, sub)
                cls.log_gui("proxy", "Disconnecting connectionid %s" % connectionid)
                try:
                    p["process"].kill()
                except AttributeError:
                    # We cannot kill thread yet
                    pass
                connections.remove(p["connection"].get_id())
                cls.update_connections(connections)
        return False

    @classmethod
    def loop(cls, once=False):
        cls.connections = cls.get_connections()
        if once:
            cls.refresh_sessions(once=True)
            st = None
        else:
            st = threading.Thread(target=cls.refresh_sessions)
            st.start()
        if once:
            cls.refresh_connections(once=True)
            ct = None
        else:
            ct = threading.Thread(target=cls.refresh_connections)
            ct.start()
        while not cls.exit:
            cls.log_debug("Proxy loop")
            time.sleep(1)
            cls.update_connections(cls.connections)
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get()
                    if not msg:
                        continue
                    if msg == Messages.EXIT:
                        break
                    elif msg.startswith(Messages.CONNECT):
                        session = Messages.get_msg_data(msg)
                        cls.connect(cls.connections, session.get_id())
                    elif msg.startswith(Messages.DISCONNECT):
                        connectionid = Messages.get_msg_data(msg)
                        cls.disconnect(cls.connections, connectionid)
                    elif msg.startswith(Messages.CONNECT_INFO):
                        connection = Connection(connection=Messages.get_msg_data(msg))
                        p = {
                            "process": False,
                            "connection": connection
                        }
                        if connection.get_parent():
                            parent = cls.connections.get(connection.get_parent())
                            if parent:
                                parent.add_children(connection.get_id())
                        cls.connections.add(connection)
                        cls.processes.append(p)
                except _queue.Empty:
                    continue
            if once:
                break

        cls.log_gui("proxy", "Proxy process exited")
        cls.exit = True
        if st:
            st.join()
        if ct:
            ct.join()
        cls.stop()

    @classmethod
    def refresh_sessions(cls, once=False):
        while not cls.exit:
            if not once:
                time.sleep(60)
            sessions = Sessions()
            cls.log_gui("proxy", "Checking sessions: %s" % repr(sessions))
            sessions.refresh_status()
            cls.log_gui("proxy", "Done checking Sessions: %s" % repr(sessions))
            if once:
                break

    @classmethod
    def refresh_connections(cls, once=False):
        while not cls.exit:
            #cls.log_gui("proxy", "Checking connections: %s" % repr(cls.connections))
            for pinfo in cls.processes.copy():
                if pinfo["process"]:
                    if isinstance(pinfo["process"], Popen):
                        alive = not pinfo["process"].poll()
                        if not alive:
                            returncode = pinfo["process"].returncode
                    else:
                        alive = pinfo["process"].is_alive()
                        if not alive:
                            returncode = None
                    if not alive:
                        cls.log_warning(
                            "Connection %s died with exit code %s" % (pinfo["connection"], returncode))
                        cls.log_gui("proxy",
                                        "Connection %s died with exit code %s" % (pinfo["connection"], returncode))
                        cls.processes.remove(pinfo)
                        conn = cls.connections.get(pinfo["connection"].get_id())
                        if conn:
                            for ch in conn.get_children():
                                cls.connections.remove(ch)
                            cls.connections.remove(conn.get_id())
                        if Registry.cfg.auto_reconnect:
                            if conn:
                                if conn.get_session().is_active():
                                    logging.getLogger("proxy").info(
                                        "Reconnecting connection %s after %s seconds" % (conn.get_id(), Registry.cfg.auto_reconnect))
                                    time.sleep(Registry.cfg.auto_reconnect)
                                    cls.myqueue.put(Messages.connect(conn.get_session()))
                                else:
                                    logging.getLogger("proxy").info(
                                        "Reconnecting connection %s after %s seconds (asking for new session)" % (conn.get_id(), Registry.cfg.auto_reconnect))
                                    time.sleep(30)
                                    session = lib.Session()
                                    session.generate(conn.get_session().get_gate().get_id(),
                                                     conn.get_session().get_space().get_id(),
                                                     conn.get_session().days())
                                    mr = lib.mngrrpc.ManagerRpcCall(conn.get_session().get_gate().get_manager_url())
                                    mrs = mr.create_session(conn.get_session().get_gate(),
                                                            conn.get_session().get_space(),
                                                            conn.get_session().days())
                                    if mrs:
                                        session = lib.Session(mrs)
                                        session.save()
                                        cls.myqueue.put(Messages.connect(session))

            cls.connections.check_alive()
            if once:
                break
            #cls.log_gui("proxy", "Checked connections: %s" % repr(cls.connections))

    @classmethod
    def stop(cls):
        cls.exit = True
        if Registry.cfg.single_thread or Registry.cfg.connect_and_exit:
            return
        else:
            for pinfo in cls.processes:
                try:
                    if pinfo["process"] and not pinfo["process"].returncode:
                        cls.log_warning("Killing subprocess with PID %s" % pinfo["process"].pid)
                        try:
                            os.kill(pinfo["process"].pid, signal.SIGINT)
                        except Exception:
                            pass
                except AttributeError:
                    pinfo["process"].kill()
                    pinfo["process"].join()
