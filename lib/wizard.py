import glob
import json
import logging
import os
import secrets
import sqlite3
import time

import nacl
import nacl.signing
import nacl.encoding
from ownca import CertificateAuthority
from copy import copy

from lib import Registry
from lib.db import DB
from lib.runcmd import RunCmd
from lib.messages import Messages
from lib.signverify import Sign, Verify
from lib.util import Util
from lib.vdp import VDP


class Wizard:

    @staticmethod
    def files(cfg, vardir=None):
        if not vardir:
            vardir = cfg.var_dir
        logging.getLogger().warning("Initializing default files")
        try:
            os.mkdir(vardir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir("%s/tmp" % vardir)
        except FileExistsError as e:
            pass

        try:
            db = DB()
            db.create_schema()
            db.close()
        except Exception as e:
            logging.error("Cannot create db %s" % cfg.db)
            raise
        vdp = VDP()
        if Registry.cfg.is_server:
            try:
                with open(Registry.cfg.provider_public_key, "r") as pf:
                    providerid = pf.read(-1).strip()
            except FileNotFoundError:
                providerid = "none"
        else:
            providerid = "none"
        files = []
        files.extend(glob.glob(cfg.app_dir + "/config/providers/*lprovider"))
        files.extend(glob.glob(cfg.app_dir + "/config/spaces/*lspace"))
        files.extend(glob.glob(cfg.app_dir + "/config/gates/*lgate"))
        for f in files:
            o = vdp.load_file(f, vdp)
            if Registry.cfg.is_server:
                if providerid == o.get_id():
                    o.set_as_local()
            o.save()
            pass
        files = []
        files.extend(glob.glob(cfg.cfg_dir + "/providers/*lprovider"))
        files.extend(glob.glob(cfg.cfg_dir + "/spaces/*lspace"))
        files.extend(glob.glob(cfg.cfg_dir + "/gates/*lgate"))
        for f in files:
            o = vdp.load_file(f, vdp)
            o.set_as_local()
            o.save()
            pass

    @staticmethod
    def cfg(cfg, p, vardir):
        if not cfg.wallet_password:
            cfg.wallet_password = secrets.token_urlsafe(12)
        with open(vardir + "/client.ini", "w") as f:
            f.write("""[global]
wallet-password = %s
wallet-rpc-password = %s
            """ % (cfg.wallet_password, cfg.wallet_rpc_password))
            pass

    @staticmethod
    def wallet(queue):
        queue.put(Messages.CREATE_WALLET)

    @staticmethod
    def ca(cfg):
        logging.getLogger("Wizard: Creating CA")
        ca = CertificateAuthority(ca_storage=cfg.ca_dir, common_name=cfg.ca_name, maximum_days=820)

    @staticmethod
    def ssh_ca(cfg):
        RunCmd.get_output(['ssh-keygen', '-t', 'ed25519', '-f', cfg.ssh_user_ca_private, '-N', ''])
        Util.set_key_permissions(cfg.ssh_user_ca_private)

    @staticmethod
    def ssh_key(cfg):
        cmd = [
            "ssh-keygen",
            "-f", cfg.ssh_user_key,
            "-C", "lvpn",
            "-t", "ed25519",
            "-N", ""
        ]
        RunCmd.get_output(cmd)

    @staticmethod
    def provider(cfg):
        logging.getLogger("Wizard: Creating Provider IDs")
        signing_key = nacl.signing.SigningKey.generate()
        verification_key = signing_key.verify_key

        # Step 2: Convert keys to bytes for storage
        signing_key_bytes = signing_key.encode(encoder=nacl.encoding.HexEncoder)
        verification_key_bytes = verification_key.encode(encoder=nacl.encoding.HexEncoder)

        with open(cfg.provider_private_key, 'wb') as private_key_file:
            private_key_file.write(signing_key_bytes)
        Util.set_key_permissions(cfg.provider_private_key)

        with open(cfg.provider_public_key, 'wb') as public_key_file:
            public_key_file.write(verification_key_bytes)

    @staticmethod
    def provider_vdp(cfg, providername="Easy LVPN provider", spacename=None, wallet="[fill-in]", host="[fill-in]", manager_url=None):
        logging.getLogger("Wizard: Creating Provider VDP")
        with open(cfg.ca_dir + "/ca.crt", "r") as cf:
            cert = cf.read(-1)
        verification_key = Verify(cfg.provider_public_key).key()
        if not spacename:
            spacename = "Easy-Free-%s" % verification_key
        if not manager_url:
            manager_url = "https://%s:8123/" % host
        provider = {
            "file_type": "LetheanProvider",
            "file_version": "1.1",
            "providerid": verification_key,
            "name": providername,
            "description": providername,
            "revision": int(time.time()),
            "ttl": 3600,
            "ca": [cert],
            "wallet": wallet,
            "manager-url": manager_url,
            "spaces": [
                spacename
            ]
        }
        spacef = {
          "file_type": "LetheanSpace",
          "file_version": "1.1",
          "spaceid": spacename.lower(),
          "providerid": verification_key,
          "name": spacename,
          "revision": int(time.time()),
          "ttl": 3600,
          "description": "Easy-provider-%s Space to access internal resources" % verification_key,
          "price": {
            "per-day": 0
          },
          "ipv4_networks": ["192.168.1.0/24"],
          "ipv6_networks": [],
          "dns_servers": ["192.168.1.1"]
        }
        spacei = {
            "file_type": "LetheanSpace",
            "file_version": "1.1",
            "spaceid": "internet",
            "providerid": verification_key,
            "revision": int(time.time()),
            "ttl": 3600,
            "name": "Easy-Internet-%s" % verification_key,
            "description": "Easy-provider-%s Space to access Internet" % verification_key,
            "price": {
                "per-day": 100
            },
            "ipv4_networks": ["192.168.1.0/24"],
            "ipv6_networks": [],
            "dns_servers": ["192.168.1.1"]
        }
        httpgatef = {
          "file_type": "LetheanGateway",
          "type": "http-proxy",
          "file_version": "1.1",
          "gateid": "free-http-proxy-tls",
          "providerid": verification_key,
          "revision": int(time.time()),
          "ttl": 3600,
          "name": "HTTP proxy to access other Lethean instances",
          "description": "Used to access internal Lethean infrastructure",
          "price": {
            "per-day": 0
          },
          "internal": True,
          "http-proxy": {
            "host": host,
            "port": 8887
          },
          "spaces": [
            "%s.free" % verification_key
          ]
        }
        httpgatei = {
            "file_type": "LetheanGateway",
            "type": "http-proxy",
            "file_version": "1.1",
            "gateid": "http-proxy-tls",
            "providerid": verification_key,
            "revision": int(time.time()),
            "ttl": 3600,
            "name": "HTTP proxy to access Internet",
            "description": "Used to access Internet",
            "price": {
                "per-day": 100
            },
            "http-proxy": {
                "host": host,
                "port": 8880
            },
            "spaces": [
                "%s.internet" % verification_key
            ]
        }
        vdp = VDP(vdpdata={
            "file_type": "VPNDescriptionProtocol",
            "file_version": "1.1",
            "providers": [provider],
            "gates": [httpgatef, httpgatei],
            "spaces": [spacef, spacei]
        })
        vdp.save()
        print(vdp.get_json(my_only=True))

