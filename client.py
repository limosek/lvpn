import os
import multiprocessing
import shutil
import sys
import tempfile
import threading
import time
import _queue
import configargparse
import logging
import logging.handlers
import secrets
import subprocess

if multiprocessing.parent_process():
    if multiprocessing.current_process().name != "GUI":
        os.environ["NO_KIVY"] = "1"

os.environ["KIVY_NO_ARGS"] = "1"
# os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
# os.environ['KIVY_NO_CONSOLELOG'] = '1'  # eliminate console log

from client.arguments import ClientArguments
from lib.arguments import SharedArguments
from client.http import Manager
from lib.mngrrpc import ManagerRpcCall
from lib.session import Session
from lib.sessions import Sessions
from lib.queue import Queue
from lib.messages import Messages
if "NO_KIVY" not in os.environ:
    from client.gui import GUI
from client.proxy import Proxy
from client.wallet import ClientWallet
from client.daemon import ClientDaemon
from lib.vdp import VDP
from lib.vdpobject import VDPException
from lib.wizard import Wizard
from client.connection import Connections
from lib.registry import Registry
from lib.wg_engine import WGEngine
from lib.runcmd import Process
import lib


def test_binary(args):
    try:
        try:
            ret = subprocess.run(args, shell=False, capture_output=True, timeout=3)
        except subprocess.TimeoutExpired:
            return True
        if ret.returncode == 0 or ret.returncode == 1:
            return True
        else:
            logging.getLogger().error("Missing binary %s" % " ".join(args))
            sys.exit(1)
    except Exception as e:
        logging.getLogger().error("Missing binary %s: %s" % (" ".join(args), e))
        sys.exit(1)


def auto_connect(ctrl, proxy_queue, wallet_queue):
    connects = Registry.cfg.auto_connect.split(",")
    active = Connections(ctrl["connections"])
    sessions = Sessions()
    if "paid" in connects:
        for session in sessions.find(paid=True, notfree=True, noparent=True):
            if not active.get_by_sessionid(session.get_id()):
                proxy_queue.put(Messages.connect(session))
                time.sleep(5)
    elif "active" in connects:
        for session in sessions.find(active=True, noparent=True):
            if not active.get_by_sessionid(session.get_id()):
                proxy_queue.put(Messages.connect(session))
                time.sleep(5)
    while not ctrl["should_exit"]:
        active = Connections(ctrl["connections"])
        for url in connects:
            if url == "active" or url == "paid":
                # We have injected active sessions already
                continue
            try:
                (gateid, spaceid) = url.split("/")
                if gateid in Registry.cfg.vdp.gate_ids() and spaceid in Registry.cfg.vdp.space_ids():
                    sess = sessions.find(gateid=gateid, spaceid=spaceid, active=True)
                    if len(sess) > 0 and not active.get_by_sessionid(sess[0]):
                        print("Trying to connect active session to %s[%s]" % (url, sess[0].get_id()))
                        proxy_queue.put(Messages.connect(sess[0]))
                        time.sleep(10)
                    else:
                        space = Registry.cfg.vdp.get_space(spaceid)
                        mr = ManagerRpcCall(space.get_manager_url())
                        try:
                            print("Trying to create session to %s" % url)
                            gate = Registry.cfg.vdp.get_gate(gateid)
                            space = Registry.cfg.vdp.get_space(spaceid)
                            if space.get_price() == 0 and gate.get_price() == 0:
                                days = Registry.cfg.free_session_days
                            else:
                                days = Registry.cfg.auto_pay_days
                            session = Session(mr.create_session(gate, space, days))
                            if session.is_fresh():
                                if Registry.cfg.auto_pay_days and not session.is_paid():
                                    for m in session.get_pay_msgs():
                                        wallet_queue.put(m)
                                session.save()
                                sessions.add(session)
                                proxy_queue.put(Messages.connect(session))
                                time.sleep(10)
                            else:
                                raise VDPException("Error requesting session from manager")
                        except Exception as e:
                            logging.getLogger("client").error("Cannot connect to %s: %s" % (gateid, e))
                            if Registry.cfg.auto_reconnect and not ctrl["should_exit"]:
                                continue
                            elif not Registry.cfg.auto_reconnect:
                                return
                else:
                    logging.getLogger("Cannot connect to autoconnect uri %s: gate or space does not exists." % (url))
                    print("Cannot connect to autoconnect uri %s: gate or space does not exists." % (url))
            except Exception as e:
                logging.getLogger("Cannot connect to autoconnect uri %s: %s" % (url, e))
        if Registry.cfg.auto_reconnect:
            if ctrl["should_exit"]:
                return
            logging.getLogger("client").warning("Waiting for %s seconds to try to reconnect." % Registry.cfg.auto_reconnect)
            for i in range(1, Registry.cfg.auto_reconnect):
                time.sleep(1)
                if ctrl["should_exit"]:
                    return
        else:
            return


def main():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        appdir = sys._MEIPASS
    else:
        appdir = os.path.dirname(os.path.abspath(__file__))

    if os.getenv("WLC_VAR_DIR"):
        vardir = os.getenv("WLC_VAR_DIR")
    else:
        vardir = os.path.expanduser("~") + "/lvpn/"

    os.environ["WLC_VAR_DIR"] = vardir

    if os.getenv("WLC_CFG_DIR"):
        cfgdir = os.getenv("WLC_CFG_DIR")
    else:
        if os.path.exists("/etc/lvpn/"):
            cfgdir = "/etc/lvpn/"
        else:
            cfgdir = os.path.expanduser("~") + "/lvpn/"
    os.environ["WLC_CFG_DIR"] = cfgdir

    if os.getenv("WLC_BIN_DIR"):
        bindir = os.getenv("WLC_BIN_DIR")
    else:
        bindir = appdir + "/bin/"

    p = configargparse.ArgParser(default_config_files=['/etc/lvpn/client.ini', cfgdir + "/client.ini", vardir + "/client.ini"])
    p = SharedArguments.define(p, os.environ["WLC_CFG_DIR"], os.environ["WLC_VAR_DIR"], os.path.dirname(__file__),
                               "WLC", "client")
    p = ClientArguments.define(p, os.environ["WLC_CFG_DIR"], os.environ["WLC_VAR_DIR"], os.path.dirname(__file__))

    cfg = p.parse_args()
    if cfg.connect_and_exit:
        cfg.auto_reconnect = 0
        cfg.wg_shutdown_on_disconnect = 0
        cfg.run_gui = 0

    cfg.l = cfg.log_level
    try:
        os.mkdir(vardir) # We need to have vardir created for logs
    except Exception as e:
        pass
    if "NO_KIVY" in os.environ:
        cfg.run_gui = 0
    if not cfg.log_file:
        cfg.log_file = vardir + "/lvpn-client.log"
    if not cfg.audit_file:
        cfg.audit_file = vardir + "/lvpn-audit.log"
    fh = logging.FileHandler(cfg.log_file)
    fh.setLevel(cfg.l)
    sh = logging.StreamHandler()
    sh.setLevel(cfg.l)
    formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET, handlers=[fh, sh])
    fh = logging.FileHandler(cfg.audit_file)
    fh.setLevel(cfg.l)
    formatter = logging.Formatter('AUDIT:%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.getLogger("audit").addHandler(fh)
    print("Logging into: %s" % vardir + "/lvpn-client.log", file=sys.stderr)
    print("Appdir: %s" % appdir, file=sys.stderr)
    print("Vardir: %s" % vardir, file=sys.stderr)

    if not cfg.wallet_rpc_password:
        cfg.wallet_rpc_password = secrets.token_urlsafe(12)

    cfg.readonly_providers = cfg.readonly_providers.split(",")

    cfg.var_dir = vardir
    cfg.bin_dir = bindir
    cfg.app_dir = appdir
    cfg.is_client = True
    cfg.is_server = False
    Registry.cfg = cfg
    wizard = False
    Wizard.files(cfg, vardir)

    if not os.path.exists(vardir + "/client.ini"):
        Wizard.cfg(cfg, p, vardir)

    os.environ['PATH'] += os.path.pathsep + appdir + "/bin"
    os.environ['PATH'] += os.path.pathsep + os.path.dirname(sys.executable)
    os.environ["NO_KIVY"] = "1"  # Set to not load KIVY for subprocesses
    print("PATH: %s" % os.environ['PATH'], file=sys.stderr)

    try:
        cfg.vdp = VDP()
    except VDPException as e:
        print(e)
        sys.exit(1)

    processes = {}
    # Hack for multiprocessing to work
    ctrl = multiprocessing.Manager().dict()
    Registry.init(cfg, ctrl, cfg.vdp)
    queue = Queue(multiprocessing.get_context(), "general")
    gui_queue = Queue(multiprocessing.get_context(), "gui")
    proxy_queue = Queue(multiprocessing.get_context(), "proxy")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    cd_queue = Queue(multiprocessing.get_context(), "daemonrpc")
    http_queue = Queue(multiprocessing.get_context(), "http")
    cfg.tmp_dir = tempfile.mkdtemp(prefix="%s/tmp/" % cfg.var_dir)
    sessions = Sessions()
    tmpdir = cfg.tmp_dir
    Messages.init_ctrl(ctrl)
    ctrl["wizard"] = wizard

    if not os.path.exists(cfg.var_dir + "/" + cfg.wallet_name):
        Wizard.wallet(wallet_queue)

    # Test binaries
    test_binary([cfg.wallet_cli_bin, "--version"])
    test_binary([cfg.wallet_rpc_bin, "--rpc-bind-port=1111", "--version"])
    if cfg.run_daemon:
        test_binary([cfg.daemon_bin, "--version"])

    os.chdir(tmpdir)
    cfg.env = os.environ.copy()
    ctrl["cfg"] = cfg
    os.environ["TEMP"] = tmpdir
    logging.getLogger().debug("Using TEMP dir %s" % tmpdir)

    if cfg.run_gui:
        os.environ["NO_KIVY"] = ""  # Set to load KIVY for gui
        gui = Process(target=GUI.run, args=[ctrl, queue, gui_queue], name="GUI")
        gui.start()
        processes["gui"] = gui
        os.environ["NO_KIVY"] = "1"  # Set to not load KIVY for subprocesses

    if cfg.run_proxy:
        proxy = Process(target=Proxy.run, args=[ctrl, queue, proxy_queue], name="Proxy")
        proxy.start()
        processes["proxy"] = proxy

    if cfg.run_wallet:
        kwargs = {}
    else:
        kwargs = {"norun": True}

    wallet = Process(target=ClientWallet.run, args=[ctrl, queue, wallet_queue], kwargs=kwargs, name="Wallet")
    wallet.start()
    processes["wallet"] = wallet
    cd = Process(target=ClientDaemon.run, args=[ctrl, queue, cd_queue], kwargs={
            "daemon_host": cfg.daemon_host,
            "daemon_port": cfg.daemon_p2p_port,
            "daemon_rpc_url": cfg.daemon_rpc_url
        }, name="Daemon")
    cd.start()
    processes["daemon"] = cd

    http = Process(target=Manager.run, args=[ctrl, queue, http_queue], kwargs={}, name="Manager")
    http.start()
    processes["http"] = http

    pids = {}
    for p in processes.values():
        pids[p.name] = p.pid
    ctrl.pids = pids

    should_exit = False
    ctrl["should_exit"] = False
    if Registry.cfg.connect_and_exit:
        auto_connect(ctrl, proxy_queue, wallet_queue)
        wallet_queue.put(Messages.EXIT)
        cd_queue.put(Messages.EXIT)
        proxy_queue.put(Messages.EXIT)
        should_exit = True
    else:
        ac = threading.Thread(target=auto_connect, args=[ctrl, proxy_queue, wallet_queue])
        ac.start()

    while not should_exit:
        logging.getLogger("client").debug("Main loop")
        for p in processes.keys():
            if not processes[p].is_alive():
                should_exit = True
                logging.getLogger("client").error(
                    "One of child process (%s,pid=%s) exited. Exiting too" % (p, processes[p].pid))
                gui_queue.put(Messages.EXIT)
                wallet_queue.put(Messages.EXIT)
                cd_queue.put(Messages.EXIT)
                break
        time.sleep(1)
        if not queue.empty():
            try:
                msg = queue.get()
            except _queue.Empty:
                continue
            if not msg:
                continue
            if Messages.is_for_main(msg):
                if msg == Messages.EXIT:
                    should_exit = True
                    logging.getLogger("client").warning("Exit requested, exiting")
                    break
            elif Messages.is_for_all(msg):
                if cfg.run_gui:
                    gui_queue.put(msg)
                if cfg.run_proxy:
                    proxy_queue.put(msg)
                if cfg.run_wallet:
                    wallet_queue.put(msg)
                    cd_queue.put(msg)
                http_queue.put(msg)
            elif Messages.is_for_gui(msg) and cfg.run_gui:
                gui_queue.put(msg)
            elif Messages.is_for_proxy(msg) and cfg.run_proxy:
                proxy_queue.put(msg)
            elif Messages.is_for_wallet(msg) and cfg.run_wallet:
                wallet_queue.put(msg)
            else:
                logging.getLogger("client").warning("Unknown msg %s requested" % msg)

    if not Registry.cfg.connect_and_exit:
        logging.getLogger().warning("Stopping all connections")
        connections = Connections(ctrl["connections"])
        connections.disconnect(proxy_queue)
        proxy_queue.put(Messages.EXIT)

    if Registry.cfg.wg_shutdown_on_disconnect:
        for iface in ctrl["wg_interfaces"]:
            WGEngine.delete_wg_interface(iface)

    logging.getLogger().warning("Waiting for subprocesses to exit")
    for p in processes.values():
        p.join(timeout=1)
    for p in processes.values():
        p.kill()
        while p.is_alive():
            time.sleep(0.1)
    proxy_queue.close()
    wallet_queue.close()
    gui_queue.close()
    ctrl["should_exit"] = True
    if not Registry.cfg.connect_and_exit:
        ac.join()
    time.sleep(3)
    try:
        shutil.rmtree(tmpdir)
    except Exception as e:
        pass


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
