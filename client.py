import os
import multiprocessing
import shutil
import sys
import tempfile
import time
import _queue
import configargparse
import logging
import logging.handlers
import secrets
import subprocess

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KCFG_KIVY_LOG_LEVEL"] = "debug"
# os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
# os.environ['KIVY_NO_CONSOLELOG'] = '1'  # eliminate console log

from lib.authids import AuthIDs
from lib.queue import Queue
from lib.runcmd import RunCmd
from lib.shared import Messages
if "NO_KIVY" not in os.environ:
    from client.gui import GUI
from client.proxy import Proxy
from client.wallet import ClientWallet
from client.daemon import ClientDaemon
from lib.vdp import VDP
from lib.vdpobject import VDPException
from lib.wizard import Wizard


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
    if os.getenv("WLC_CONFIG_DIR"):
        cfgdir = os.getenv("WLC_CONFIG_DIR")
    else:
        if os.path.exists("/etc/lvpn/"):
            cfgdir = "/etc/lvpn/"
        else:
            cfgdir = os.path.expanduser("~") + "/lvpn/"
    if os.getenv("WLC_BIN_DIR"):
        bindir = os.getenv("WLC_BIN_DIR")
    else:
        bindir = appdir + "/bin/"

    p = configargparse.ArgParser(default_config_files=['/etc/lvpn/client.ini', cfgdir + "/client.ini", vardir + "/client.ini"])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path')
    p.add_argument('--wallet-rpc-bin', help='Wallet RPC binary file')
    p.add_argument('--wallet-cli-bin', help='Wallet CLI binary file')
    p.add_argument('--daemon-rpc-bin', help='Daemon-RPC binary file')
    p.add_argument('--daemon-bin', help='Daemon binary file')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                   env_var='WLC_LOGLEVEL')
    p.add_argument("--spaces-dir", help="Directory containing all spaces VDPs", default=os.path.abspath(vardir + "/spaces"))
    p.add_argument("--gates-dir", help="Directory containing all gateway VDPs", default=os.path.abspath(vardir + "/gates"))
    p.add_argument("--providers-dir", help="Directory containing all provider VDPs",
                   default=os.path.abspath(vardir + "/providers"))
    p.add_argument("--authids-dir", help="Directory containing all authids", default=os.path.abspath(vardir + "/authids"))
    p.add_argument("--coin-type", help="Coin type to sue", default="lethean", type=str, choices=["lethean", "monero"],
                   env_var="WLC_COINTYPE")
    p.add_argument("--coin-unit", help="Coin minimal unit", type=float)
    p.add_argument('--run-gui', default=1, type=int, choices=[0, 1], help='Run GUI')
    p.add_argument('--run-proxy', default=1, type=int, choices=[0, 1], help='Run local proxy')
    p.add_argument('--run-wallet', default=1, type=int, choices=[0, 1], help='Run local wallet')
    p.add_argument('--run-daemon', default=0, type=int, choices=[0, 1], help='Run local daemon RPC')
    p.add_argument('--edge-bin', help='Edge browser binary',
                   default="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    p.add_argument('--chromium-bin', help='Chromium browser binary', default="chromium")
    p.add_argument('--daemon-host', help='Daemon host', default='localhost')
    p.add_argument('--daemon-p2p-port', help='Daemon P2P port', type=int)
    p.add_argument('--daemon-rpc-url', help='Daemon RPC URL')
    p.add_argument('--wallet-rpc-url', help='Wallet RPC URL', default='http://localhost:1444/json_rpc')
    p.add_argument('--wallet-rpc-port', help='Wallet RPC port', type=int, default=1444)
    p.add_argument('--wallet-rpc-user', help='Wallet RPC user', default='vpn')
    p.add_argument('--wallet-rpc-password', help='Wallet RPC password. Default is to generate random')
    p.add_argument('--wallet-name', help='Wallet name')
    p.add_argument('--wallet-password', help='Wallet password')
    p.add_argument('--use-http-proxy', type=str, help='Use HTTP proxy (CONNECT) to services', env_var="HTTP_PROXY")
    p.add_argument('--auto-connect', type=str, help='Auto connect uris',
                       default="fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671.free-ssh/fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671.free"
                   )
    p.add_argument("cmd", help="Choose command", nargs="*", type=str)

    cfg = p.parse_args()
    try:
        os.mkdir(vardir) # We need to have vardir created for logs
    except Exception as e:
        pass
    if "NO_KIVY" in os.environ:
        cfg.run_gui = 0
    fh = logging.FileHandler(vardir + "/lvpn-client.log")
    fh.setLevel(cfg.l)
    sh = logging.StreamHandler()
    sh.setLevel(cfg.l)
    formatter = logging.Formatter('%(name)s[%(process)d]:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET, handlers=[fh, sh])
    print("Logging into: %s" % vardir + "/lvpn-client.log", file=sys.stderr)
    print("Appdir: %s" % appdir, file=sys.stderr)
    print("Vardir: %s" % vardir, file=sys.stderr)

    if not cfg.wallet_rpc_password:
        cfg.wallet_rpc_password = secrets.token_urlsafe(12)

    cfg.var_dir = vardir
    cfg.bin_dir = bindir
    cfg.app_dir = appdir
    wizard = False
    Wizard().files(cfg, vardir)

    if not os.path.exists(vardir + "/client.ini"):
        Wizard().cfg(cfg, p, vardir)

    os.environ['PATH'] += os.path.pathsep + appdir + "/bin"
    os.environ['PATH'] += os.path.pathsep + os.path.dirname(sys.executable)
    print("PATH: %s" % os.environ['PATH'], file=sys.stderr)
    # Initialize RunCmd
    RunCmd.init(cfg)

    if cfg.coin_type == "lethean":
        if not cfg.wallet_rpc_bin:
            cfg.wallet_rpc_bin = "lethean-wallet-rpc"
        if not cfg.wallet_cli_bin:
            cfg.wallet_cli_bin = "lethean-wallet-cli"
        if not cfg.daemon_rpc_url:
            cfg.daemon_rpc_url = "http://localhost:48782/json_rpc"
        if not cfg.daemon_bin:
            cfg.daemon_bin = "letheand"
        if not cfg.daemon_p2p_port:
            cfg.daemon_p2p_port = 48772
        if not cfg.wallet_name:
            cfg.wallet_name = "wallet-lthn"
        if not cfg.coin_unit:
            cfg.coin_unit = 1e-8
    elif cfg.coin_type == "monero":
        if not cfg.wallet_rpc_bin:
            cfg.wallet_rpc_bin = "monero-wallet-rpc"
        if not cfg.daemon_rpc_url:
            cfg.daemon_rpc_url = "http://localhost:18081/json_rpc"
        if not cfg.daemon_p2p_port:
            cfg.daemon_p2p_port = 18080
        if not cfg.wallet_name:
            cfg.wallet_name = "wallet-monero"
        if not cfg.coin_unit:
            cfg.coin_unit = 1e-12

    if not os.path.exists(cfg.var_dir + "/" + cfg.wallet_name):
        wizard = True

    try:
        cfg.vdp = VDP(cfg)
    except VDPException as e:
        print(e)
        sys.exit(1)

    processes = {}
    # Hack for multiprocessing to work
    sys._base_executable = sys.executable
    ctrl = multiprocessing.Manager().dict()
    queue = Queue(multiprocessing.get_context(), "general")
    gui_queue = Queue(multiprocessing.get_context(), "gui")
    proxy_queue = Queue(multiprocessing.get_context(), "proxy")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    cd_queue = Queue(multiprocessing.get_context(), "daemonrpc")
    cfg.tmp_dir = tempfile.mkdtemp(prefix="%s/tmp/" % cfg.var_dir)
    cfg.authids = AuthIDs(cfg.authids_dir)
    tmpdir = cfg.tmp_dir
    ctrl["log"] = ""
    ctrl["daemon_height"] = -1
    ctrl["selected_gate"] = None
    ctrl["selected_space"] = None
    ctrl["connections"] = []
    ctrl["wallet_address"] = ""
    ctrl["payments"] = {}
    ctrl["balance"] = -1
    ctrl["unlocked_balance"] = -1
    ctrl["wallet_height"] = -1
    ctrl["wallet_address"] = ""
    ctrl["wizard"] = wizard

    if cfg.cmd:

        if cfg.cmd[0] == "connect":
            if len(cfg.cmd) == 2:
                ctrl["cfg"] = cfg
                url = cfg.cmd[1]
                (gateid, spaceid) = url.split("/")
                if gateid in cfg.vdp.gate_ids() and spaceid in cfg.vdp.space_ids():
                    proxy_queue.put(Messages.connect(cfg.vdp.get_space(spaceid), cfg.vdp.get_gate(gateid), None))
                else:
                    logging.getLogger("Cannot connect to connect uri %s: gate or space does not exists." % (url))
                Proxy.run(ctrl, queue, proxy_queue)
                sys.exit()
            else:
                logging.getLogger().error("You need to specify connect uri")
                sys.exit(1)

        elif cfg.cmd[0] == "list-spaces":
            print("id,name")
            for s in cfg.vdp.spaces():
                print("%s,%s" % (s.get_id(), s.get_name()))
            sys.exit()

        elif cfg.cmd[0] == "list-gates":
            print("id,type,internal,name")
            for s in cfg.vdp.gates():
                print("%s,%s,%s,%s" % (s.get_id(), s.get_type(), s.is_internal(), s.get_name()))
            sys.exit()

        elif cfg.cmd[0] == "create-wallet":
            if cfg.wallet_name and cfg.wallet_password:
                logging.getLogger().warning("Creating wallet")
                wallet_queue.put(Messages.CREATE_WALLET)
            else:
                logging.getLogger().error("You need to specify --wallet-name and --wallet-password.")
                sys.exit(1)

        elif cfg.cmd[0] == "import-wallet":
            if not cfg.wallet_name and cfg.wallet_password:
                logging.getLogger().error("You need to specify --wallet-name and --wallet-password.")
                sys.exit(1)
            if len(cfg.cmd) < 2:
                logging.error(
                    "Use import-wallet 'seed'")
                sys.exit(2)
            else:
                seed = " ".join(cfg.cmd[1:])
                wallet_queue.put(Messages.wallet_restore(seed))
            pass

        elif cfg.cmd[0] == "import-vdp":
            if len(cfg.cmd) == 2:
                vdp = VDP(cfg.cmd[1])
                vdp.save(cfg.gates_dir, cfg.spaces_dir)
                sys.exit()
            else:
                logging.error(
                    "Use import-vdp file-or-url")

        elif cfg.cmd[0] == "test-gui":
            cfg.authids = AuthIDs(cfg.authids_dir)
            cfg.vdp = VDP(gates_dir=cfg.gates_dir, spaces_dir=cfg.spaces_dir)
            ctrl["cfg"] = cfg
            ctrl["tmpdir"] = tmpdir
            GUI.run(ctrl=ctrl, queue=queue, myqueue=gui_queue)
            sys.exit()

        elif cfg.cmd[0] == "run":
            print("run")

        else:
            logging.error(
                "Bad command '%s'. Use one of connect,create-wallet,run,wizard,import-vdp" % " ".join(cfg.cmd))
            sys.exit(1)
    else:
        cfg.cmd = ["run"]

    # Test binaries
    test_binary([cfg.wallet_cli_bin, "--version"])
    test_binary([cfg.wallet_rpc_bin, "--rpc-bind-port=1111", "--version"])
    if cfg.run_daemon:
        test_binary([cfg.daemon_bin, "--version"])

    for url in cfg.auto_connect.split(","):
        print("Trying to connect to %s" % url)
        try:
            (gateid, spaceid) = url.split("/")
            if gateid in cfg.vdp.gate_ids() and spaceid in cfg.vdp.space_ids():
                proxy_queue.put(Messages.connect(cfg.vdp.get_space(spaceid), cfg.vdp.get_gate(gateid), None))
            else:
                logging.getLogger("Cannot connect to autoconnect uri %s: gate or space does not exists." % (url))
                print("Cannot connect to autoconnect uri %s: gate or space does not exists." % (url))
        except Exception as e:
            logging.getLogger("Cannot connect to autoconnect uri %s: %s" % (url, e))

    os.chdir(tmpdir)
    cfg.env = os.environ.copy()
    ctrl["cfg"] = cfg
    ctrl["tmpdir"] = tmpdir
    os.environ["TEMP"] = tmpdir
    logging.getLogger().debug("Using TEMP dir %s" % tmpdir)

    if cfg.run_gui:
        gui = multiprocessing.Process(target=GUI.run, args=[ctrl, queue, gui_queue], name="GUI")
        gui.start()
        processes["gui"] = gui

    if cfg.run_proxy:
        proxy = multiprocessing.Process(target=Proxy.run, args=[ctrl, queue, proxy_queue], name="Proxy")
        proxy.start()
        processes["proxy"] = proxy

    if cfg.run_wallet:
        wallet = multiprocessing.Process(target=ClientWallet.run, args=[ctrl, queue, wallet_queue], kwargs={}, name="Wallet")
        wallet.start()
        processes["wallet"] = wallet
        cd = multiprocessing.Process(target=ClientDaemon.run, args=[ctrl, queue, cd_queue], kwargs=
        {
            "daemon_host": cfg.daemon_host,
            "daemon_port": cfg.daemon_p2p_port,
            "daemon_rpc_url": cfg.daemon_rpc_url
        }, name="Daemon")
        cd.start()
        processes["daemon"] = cd

    pids = {}
    for p in processes.values():
        pids[p.name] = p.pid
    ctrl.pids = pids

    should_exit = False
    while not should_exit:
        logging.getLogger("client").debug("Main loop")
        for p in processes.keys():
            if not processes[p].is_alive():
                should_exit = True
                logging.getLogger("client").error(
                    "One of child process (%s,pid=%s) exited. Exiting too" % (p, processes[p].pid))
                gui_queue.put(Messages.EXIT)
                proxy_queue.put(Messages.EXIT)
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
                elif Messages.is_for_gui(msg) and cfg.run_gui:
                    gui_queue.put(msg)
                elif Messages.is_for_proxy(msg) and cfg.run_proxy:
                    proxy_queue.put(msg)
                elif Messages.is_for_wallet(msg) and cfg.run_wallet:
                    wallet_queue.put(msg)
                else:
                    logging.getLogger("client").warning("Unknown msg %s requested, exiting" % msg)
                    should_exit = True
                    break

    logging.getLogger().warning("Waiting for subprocesses to exit")
    for p in processes.values():
        p.join(timeout=1)
    for p in processes.values():
        p.kill()
        while p.is_alive():
            time.sleep(0.1)
    time.sleep(3)
    try:
        shutil.rmtree(tmpdir)
    except Exception as e:
        pass


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
