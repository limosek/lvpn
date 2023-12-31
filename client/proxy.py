import copy
import os
import signal
import subprocess
import logging
import sys
import time
import socket
from contextlib import closing

import _queue

from lib.runcmd import RunCmd
from lib.service import Service
from lib.shared import Messages


class Proxy(Service):
    myname = "proxy"
    processes = []

    @classmethod
    def find_free_port(cls):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

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
        return RunCmd.popen(args, cwd=cls.ctrl["tmpdir"], shell=False)

    @classmethod
    def run_http_proxy(cls, cafile, localport, endpoint):
        (host, port) = endpoint.split(":")
        args = [
            "-C", cafile,
            "-p", str(localport),
            "-n", "10",
            "-T", "300",
            host, port
        ]
        logging.getLogger("proxy").warning("Running ptw http-proxy subprocess: %s" % " ".join(args))
        return cls.run_ptw(args)

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
        logging.getLogger("proxy").warning("Running ptw socks-proxy subprocess: %s" % " ".join(args))
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
        logging.getLogger("proxy").warning("Running ptw daemon-p2p-proxy subprocess: %s" % " ".join(args))
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
        logging.getLogger("proxy").warning("Running ptw daemon-rpc-proxy subprocess: %s" % " ".join(args))
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
    def connect(cls, space, gate, authid):
        if not gate.is_for_space(space.get_id()):
            logging.getLogger("proxy").error("Gate %s is not allowed to connect to space %s" % (gate, space))
            cls.log_message("proxy", "Gate %s is not allowed to connect to space %s" % (gate, space))
            return
        if gate.get_type() == "http-proxy":
            port = "8080"
            cls.processes.append(
              {
                "process": cls.run_http_proxy(gate.get_cafile(cls.ctrl["tmpdir"]), port,
                                              gate.get_endpoint()),
                "space": space,
                "gate": gate,
                "endpoint": gate.get_endpoint(),
                "authid": authid,
                "port": port
              }
            )
            cls.log_message("proxy", "Connecting to gate %s and space %s" % (gate, space))
        elif gate.get_type() == "daemon-rpc-proxy":
            cls.processes.append(
                {
                    "process": cls.run_daemon_rpc_proxy(gate.get_cafile(cls.ctrl["tmpdir"]), 48782,
                                                        gate.get_endpoint()),
                    "space": space,
                    "gate": gate,
                    "endpoint": gate.get_endpoint(),
                    "authid": authid,
                    "port": 48782
                }
            )
            cls.log_message("proxy", "Connecting to gate %s and space %s" % (gate, space))

        elif gate.get_type() == "daemon-p2p-proxy":
            cls.processes.append(
                {
                    "process": cls.run_socks_proxy(gate.get_cafile(cls.ctrl["tmpdir"]), 48772,
                                                        gate.get_endpoint()),
                    "space": space,
                    "gate": gate,
                    "endpoint": gate.get_endpoint(),
                    "authid": authid,
                    "port": 48772
                }
            )
            cls.log_message("proxy", "Connecting to gate %s and space %s" % (gate, space))
        elif gate.get_type() == "socks-proxy":
            cls.processes.append(
                {
                    "process": cls.run_daemon_p2p_proxy(gate.get_cafile(cls.ctrl["tmpdir"]), 8081,
                                                        gate.get_endpoint()),
                    "space": space,
                    "gate": gate,
                    "endpoint": gate.get_endpoint(),
                    "authid": authid,
                    "port": 8081
                }
            )
            cls.log_message("proxy", "Connecting to gate %s and space %s" % (gate, space))
        else:
            logging.getLogger("proxy").error("Unknown gate type %s" % gate.get_type())
            cls.log_message("proxy", "Unknown gate type %s" % gate.get_type())

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
                cls.log_message("proxy", "Disconnecting gate %s and space %s" % (gateid, spaceid))
                c["process"].kill()
        return False

    @classmethod
    def loop(cls):
        while not cls.exit:
            logging.getLogger("proxy").debug("Proxy loop")
            connections = []
            for pinfo in cls.processes.copy():
                if pinfo["process"] and pinfo["process"].poll():
                    logging.getLogger("proxy").warning(
                        "Connection %s/%s died with exit code %s" % (pinfo["gate"], pinfo["space"],
                                                                     pinfo["process"].returncode))
                    cls.log_message("proxy",
                                    "Connection %s/%s died with exit code %s" % (pinfo["gate"], pinfo["space"],
                                                                                 pinfo["process"].returncode))
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
                        space = cls.ctrl["cfg"].vdp.get_space(cdata["spaceid"])
                        gate = cls.ctrl["cfg"].vdp.get_gate(cdata["gateid"])
                        if "authid" in cdata:
                            authid = cls.ctrl["cfg"].authids.find(cdata["gateid"])
                        else:
                            authid = None
                        cls.connect(space, gate, authid)
                    elif msg.startswith(Messages.DISCONNECT):
                        cdata = Messages.get_msg_data(msg)
                        cls.disconnect(cdata["gateid"], cdata["spaceid"])
                except _queue.Empty:
                    continue

        cls.log_message("proxy", "Proxy process exited")
        cls.stop()

    @classmethod
    def stop(cls):
        cls.exit = True
        for pinfo in cls.processes:
            if pinfo["process"] and not pinfo["process"].returncode:
                logging.getLogger("proxy").warning("Killing subprocess with PID %s" % pinfo["process"].pid)
                os.kill(pinfo["process"].pid, signal.SIGINT)
                #pinfo["process"].communicate()
