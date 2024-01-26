import copy
import multiprocessing
import os
import secrets
import signal
import logging
import sys
import time
import _queue

from client.sshproxy import SSHProxy
from client.tlsproxy import TLSProxy
from lib.runcmd import RunCmd
from lib.service import Service
from lib.shared import Messages


class Proxy(Service):
    myname = "proxy"
    processes = []

    @classmethod
    def run_ptw(cls, pargs):
        args = [sys.executable, cls.ctrl["cfg"].app_dir + "/ptwbin.py"]
        if cls.ctrl["cfg"].l == "DEBUG":
            args.extend(["-v", "debug"])
        elif cls.ctrl["cfg"].l == "INFO":
            args.extend(["-v", "info"])
        else:
            args.extend(["-v", "warning"])
        args.extend(list(pargs))
        args.append("--no-hostname-check")
        return RunCmd.popen(args, cwd=cls.ctrl["tmpdir"], shell=False)

    @classmethod
    def run_socks_proxy(cls, cafile, localport, endpoint):
        (host, port) = endpoint.split(":")
        args = [
            "-C", cafile,
            "-p", str(localport),
            "-n", "10",
            "-T", "300",
            host, port
        ]
        cls.log_warning("Running ptw socks-proxy subprocess: %s" % " ".join(args))
        return cls.run_ptw(args)

    @classmethod
    def run_daemon_p2p_proxy(cls, cafile, localport, endpoint):
        (host, port) = endpoint.split(":")
        args = [
            "-C", cafile,
            "-p", str(localport),
            "-n", "1",
            "-T", "30",
            host, port
        ]
        cls.log_warning("Running ptw daemon-p2p-proxy subprocess: %s" % " ".join(args))
        return cls.run_ptw(args)

    @classmethod
    def run_daemon_rpc_proxy(cls, cafile, localport, endpoint):
        (host, port) = endpoint.split(":")
        args = [
            "-C", cafile,
            "-p", str(localport),
            "-n", "5",
            "-T", "30",
            host, port
        ]
        cls.log_warning("Running ptw daemon-rpc-proxy subprocess: %s" % " ".join(args))
        return cls.run_ptw(args)

    @classmethod
    def run(cls, ctrl, queue, myqueue, cafile=None, localhttp=None, localsocks=None, localrpc=None, localp2p=None, httpendpoint=None, socksendpoint=None, rpcendpoint=None, p2pendpoint=None):
        cls.ctrl = ctrl
        cls.queue = queue
        cls.myqueue = myqueue
        cls.processes = []
        cls.ctrl["connections"] = []
        logging.basicConfig(level=ctrl["cfg"].l)
        RunCmd.init(cls.ctrl["cfg"])
        super().run(ctrl, queue, myqueue)

    @classmethod
    def run_tls_proxy(cls, port, gate, space, authid):
        mp = multiprocessing.Process(target=TLSProxy.run, args=[cls.ctrl, cls.queue, None], kwargs={
            "gate": gate,
            "space": space,
            "authid": authid,
            "port": port
        })
        mp.start()
        cls.processes.append(
            {
                "process": mp,
                "space": space,
                "gate": gate,
                "endpoint": gate.get_endpoint(),
                "authid": authid,
                "port": port
            }
        )
        cls.log_gui("proxy", "Connecting to gate %s and space %s" % (gate, space))

    @classmethod
    def connect(cls, space, gate, authid):
        if not gate.is_for_space(space.get_id()):
            cls.log_error("Gate %s is not allowed to connect to space %s" % (gate, space))
            cls.log_gui("proxy", "Gate %s is not allowed to connect to space %s" % (gate, space))
            return
        if gate.get_type() in ["http-proxy", "daemon-rpc", "daemon-p2p", "socks-proxy"]:
            cls.run_tls_proxy(gate.get_local_port(), gate, space, authid)
        elif gate.get_type() == "ssh":
            args = [cls.ctrl, cls.queue, None]
            kwargs = {
                "gate": gate,
                "space": space,
                "authid": authid,
                "connectionid": secrets.token_urlsafe(6)
            }
            mp = multiprocessing.Process(target=SSHProxy.run, args=args, kwargs=kwargs)
            mp.start()
            p = {
                    "process": mp,
                    "space": space,
                    "gate": gate,
                    "endpoint": gate.get_endpoint(),
                    "authid": authid,
                    "port": "NA",
                    "connectionid": secrets.token_urlsafe(6)
                }
            cls.processes.append(p)
            cls.log_gui("proxy", "Connecting to gate %s and space %s" % (gate, space))
        else:
            cls.log_error("Unknown gate type %s" % gate.get_type())
            cls.log_gui("proxy", "Unknown gate type %s" % gate.get_type())

    @classmethod
    def get_connections(cls):
        return cls.get_value("connections")

    @classmethod
    def is_connected(cls, spaceid, gateid):
        for c in cls.get_value("connections"):
            if c["space"].get_id() == spaceid:
                return True
            if c["gate"].get_id() == gateid:
                return True
        return False

    @classmethod
    def disconnect(cls, gateid, spaceid):
        for c in cls.processes:
            if c["space"].get_id() == spaceid and c["gate"].get_id() == gateid:
                cls.log_gui("proxy", "Disconnecting gate %s and space %s" % (gateid, spaceid))
                try:
                    c["process"].kill()
                except AttributeError:
                    # We cannot kill thread yet
                    pass
        return False

    @classmethod
    def find_process_by_pid(cls, pid):
        for p in cls.processes:
            if p["process"].pid == pid:
                return p["process"]
        else:
            return None

    @classmethod
    def loop(cls):
        while not cls.exit:
            cls.log_debug("Proxy loop")
            connections = []
            for pinfo in cls.processes.copy():
                if pinfo["process"]:
                    try:
                        if pinfo["process"].poll():
                            cls.log_warning(
                                "Connection %s/%s died with exit code %s" % (pinfo["gate"], pinfo["space"],
                                                                             pinfo["process"].returncode))
                            cls.log_gui("proxy",
                                            "Connection %s/%s died with exit code %s" % (pinfo["gate"], pinfo["space"],
                                                                                         pinfo["process"].returncode))
                            cls.processes.remove(pinfo)
                            break
                    except AttributeError:
                        if not pinfo["process"].is_alive():
                            cls.log_warning(
                                "Connection %s/%s died" % (pinfo["gate"], pinfo["space"]))
                            cls.log_gui("proxy",
                                            "Connection %s/%s died" % (pinfo["gate"], pinfo["space"]))
                            cls.processes.remove(pinfo)
                            break
                pinfo2 = copy.copy(pinfo)
                del(pinfo2["process"])
                connections.append(pinfo2)
            cls.set_value("connections", connections)
            time.sleep(1)
            if not cls.myqueue.empty():
                try:
                    msg = cls.myqueue.get()
                    if not msg:
                        continue
                    if msg == Messages.EXIT:
                        break
                    elif msg.startswith(Messages.CONNECT):
                        cdata = Messages.get_msg_data(msg)
                        if "authid" in cdata:
                            authid = cls.ctrl["cfg"].sessions.find_for_gate(cdata["gate"].get_id())
                        else:
                            authid = None
                        cls.connect(cdata["space"], cdata["gate"], authid)
                    elif msg.startswith(Messages.DISCONNECT):
                        cdata = Messages.get_msg_data(msg)
                        cls.disconnect(cdata["gateid"], cdata["spaceid"])
                    elif msg.startswith(Messages.CONNECT_INFO):
                        data = Messages.get_msg_data(msg)
                        p = {
                            "process": cls.find_process_by_pid(data["data"]["pid"]),
                            "space": data["space"],
                            "gate": data["gate"],
                            "endpoint": data["gate"].get_endpoint(),
                            "authid": data["authid"],
                            "ports": data["data"]["ports"],
                            "port": data["data"]["port"],
                            "connectionid": data["data"]["connectionid"]
                        }
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
