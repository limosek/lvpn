import os
import multiprocessing
import shutil
import sys
import tempfile
import time
import configargparse
import logging
import logging.handlers
import secrets
import subprocess
from lib.authids import AuthIDs
from lib.queue import Queue
from lib.runcmd import RunCmd
from lib.shared import Messages
from client.gui import GUI
from client.proxy import Proxy
from client.wallet import ClientWallet
from client.daemon import ClientDaemon
from lib.vdp import VDP
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
            logging.getLogger().error("Missing binary %s" % args[0])
            sys.exit(1)
    except Exception as e:
        logging.getLogger().error("Missing binary %s: %s" % (args[0], e))
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
    p.add_argument('--ptw-bin', default="ptw")
    p.add_argument('--wallet-rpc-bin', help='Wallet RPC binary file')
    p.add_argument('--wallet-cli-bin', help='Wallet CLI binary file')
    p.add_argument('--daemon-rpc-bin', help='Daemon binary file')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                   env_var='WLC_LOGLEVEL')
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs", default=os.path.abspath(vardir + "/spaces"))
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs", default=os.path.abspath(vardir + "/gates"))
    p.add_argument("--authids-dir", help="Directory containing all authids", default=os.path.abspath(vardir + "/authids"))
    p.add_argument("--coin-type", help="Coin type to sue", default="lethean", type=str, choices=["lethean", "monero"],
                   env_var="WLC_COINTYPE")
    p.add_argument("--coin-unit", help="Coin minimal unit", type=float)
    p.add_argument('--run-gui', default=1, type=int, choices=[0, 1], help='Run GUI')
    p.add_argument('--run-proxy', default=1, type=int, choices=[0, 1], help='Run local proxy')
    p.add_argument('--run-wallet', default=1, type=int, choices=[0, 1], help='Run local wallet')
    p.add_argument('--run-daemon', default=0, type=int, choices=[0, 1], help='Run local daemon RPC')
    p.add_argument('--chromium-bin', help='Chromium browser binary')
    p.add_argument('--daemon-host', help='Daemon host', default='localhost')
    p.add_argument('--daemon-p2p-port', help='Daemon P2P port', type=int)
    p.add_argument('--daemon-rpc-url', help='Daemon RPC URL')
    p.add_argument('--wallet-rpc-url', help='Wallet RPC URL', default='http://localhost:1444/json_rpc')
    p.add_argument('--wallet-rpc-port', help='Wallet RPC port', type=int, default=1444)
    p.add_argument('--wallet-rpc-user', help='Wallet RPC user', default='vpn')
    p.add_argument('--wallet-rpc-password', help='Wallet RPC password. Default is to generate random')
    p.add_argument('--wallet-name', help='Wallet name')
    p.add_argument('--wallet-password', help='Wallet password')
    p.add_argument("cmd", help="Choose command", nargs="*", type=str)

    try:
        cfg = p.parse_args()
    except SystemExit:
        print("Bad configuration or commandline argument.")
        print(p.format_usage())
        sys.exit(1)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    fh = logging.FileHandler(vardir + "/lvpn-client.log")
    fh.setLevel(cfg.l)
    formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET, handlers=[fh])
    print("Logging into: %s" % vardir + "/lvpn-client.log")
    print("Appdir: %s" % appdir)
    print("Vardir: %s" % vardir)

    if not cfg.wallet_rpc_password:
        cfg.wallet_rpc_password = secrets.token_urlsafe(12)

    cfg.var_dir = vardir
    cfg.bin_dir = bindir
    cfg.app_dir = appdir
    wizard = False
    if not os.path.exists(vardir) or not os.path.exists(cfg.gates_dir) or not os.path.exists(cfg.spaces_dir):
        Wizard().files(cfg, vardir)
        wizard = True

    if not os.path.exists(vardir + "/client.ini"):
        Wizard().cfg(cfg, p, vardir)

    os.environ['PATH'] += os.path.pathsep + appdir + "/bin"
    os.environ['PATH'] += os.path.pathsep + os.path.dirname(sys.executable)
    print("PATH: %s" % os.environ['PATH'])
    # Initialize RunCmd
    RunCmd.init(cfg)

    if cfg.coin_type == "lethean":
        if not cfg.wallet_rpc_bin:
            cfg.wallet_rpc_bin = "lethean-wallet-rpc"
        if not cfg.wallet_cli_bin:
            cfg.wallet_cli_bin = "lethean-wallet-cli"
        if not cfg.daemon_rpc_url:
            cfg.daemon_rpc_url = "http://localhost:48782/json_rpc"
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

    processes = {}
    ctrl = multiprocessing.Manager().dict()
    queue = Queue(multiprocessing.get_context(), "general")
    gui_queue = Queue(multiprocessing.get_context(), "gui")
    proxy_queue = Queue(multiprocessing.get_context(), "proxy")
    wallet_queue = Queue(multiprocessing.get_context(), "wallet")
    cd_queue = Queue(multiprocessing.get_context(), "daemonrpc")
    cfg.tmp_dir = tempfile.mkdtemp(prefix="%s/tmp/" % cfg.var_dir)
    tmpdir = cfg.tmp_dir
    default_cmd = False
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
            print("connect")

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
        default_cmd = True

    # Test binaries
    test_binary([cfg.wallet_cli_bin, "--version"])
    test_binary([cfg.wallet_rpc_bin, "--rpc-bind-port=1111", "--version"])
    test_binary(["ptw", "-h"])

    cfg.vdp = VDP(gates_dir=cfg.gates_dir, spaces_dir=cfg.spaces_dir)
    if default_cmd:
        if "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean-daemon-rpc-http" in cfg.vdp.gate_ids() \
                and "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean" in cfg.vdp.space_ids():
            proxy_queue.put(Messages.connect("fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean",
                                             "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean-daemon-rpc-http",
                                             None))
        if "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean-daemon-p1p-tls" in cfg.vdp.gate_ids() \
                and "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean" in cfg.vdp.space_ids():
            proxy_queue.put(Messages.connect("fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean",
                                         "fbf893c4317c6938750fc0532becd25316cd77406cd52cb81768164608515671-lethean-daemon-p1p-tls",
                                         None))
    cfg.authids = AuthIDs(cfg.authids_dir)
    os.chdir(tmpdir)
    ctrl["cfg"] = cfg
    ctrl["tmpdir"] = tmpdir
    os.environ["TEMP"] = tmpdir
    logging.getLogger().debug("Using TEMP dir %s" % tmpdir)

    if cfg.run_daemon:
        logging.error("Running local daemon is not supported yet.")
        sys.exit(1)

    if cfg.run_gui:
        gui = multiprocessing.Process(target=GUI.run, args=[ctrl, queue, gui_queue], name="GUI")
        gui.start()
        processes["gui"] = gui

    if cfg.run_proxy:
        proxy = multiprocessing.Process(target=Proxy.run, args=[ctrl, queue, proxy_queue], name="Proxy")
        proxy.start()
        processes["proxy"] = proxy

    if cfg.run_wallet:
        wallet = multiprocessing.Process(target=ClientWallet.run, args=[ctrl, queue, wallet_queue], kwargs=
        {}, name="Wallet")
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
                msg = queue.get()
                print(msg)
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
