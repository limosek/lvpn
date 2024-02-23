import json
import logging
import os
import secrets

import nacl
import nacl.signing
import nacl.encoding
from ownca import CertificateAuthority
from copy import copy

from lib.runcmd import RunCmd
from lib.messages import Messages
from lib.signverify import Sign, Verify
from lib.util import Util
from lib.vdp import VDP


class Wizard:

    @staticmethod
    def files(cfg, vardir=None):
        cfgc = copy(cfg)
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
            os.mkdir(cfg.gates_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.spaces_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.providers_dir)
        except FileExistsError as e:
            pass

        try:
            os.mkdir(cfg.sessions_dir)
        except FileExistsError as e:
            pass

        v = VDP()
        v.save(cfgc)

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
    def provider_vdp(cfg, providername="Easy LVPN provider", spacename="free", wallet="[fill-in]", host="[fill-in]"):
        logging.getLogger("Wizard: Creating Provider VDP")
        with open(cfg.ca_dir + "/ca.crt", "r") as cf:
            cert = cf.read(-1)
        verification_key = Verify(cfg.provider_public_key).key()
        provider = {
            "file_type": "LetheanProvider",
            "file_version": "1.1",
            "providerid": verification_key,
            "name": providername,
            "description": providername,
            "ca": [cert],
            "wallet": wallet,
            "manager-url": "https://%s:8790/" % host,
            "spaces": [
                spacename
            ]
        }
        space = {
          "file_type": "LetheanSpace",
          "file_version": "1.1",
          "spaceid": spacename.lower(),
          "providerid": verification_key,
          "name": spacename,
          "description": spacename,
          "price": {
            "per-day": 0
          }
        }
        httpgate = {
          "file_type": "LetheanGateway",
          "type": "http-proxy",
          "file_version": "1.1",
          "gateid": "free-http-proxy",
          "providerid": verification_key,
          "name": "HTTP proxy to access other Lethean instances",
          "description": "Used to access internal Lethean infrastructure",
          "price": {
            "per-day": 0
          },
          "http-proxy": {
            "host": host,
            "port": 8888
          },
          "spaces": [
            "%s.free" % verification_key
          ]
        }
        vdp = VDP(vdpdata={
            "file_type": "VPNDescriptionProtocol",
            "file_version": "1.0",
            "providers": [provider],
            "gates": [httpgate],
            "spaces": [space]
        })
        vdp.save(cfg)

