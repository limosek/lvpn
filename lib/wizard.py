import json
import logging
import os
import secrets

import nacl
import nacl.signing
import nacl.encoding
from ownca import CertificateAuthority
from copy import copy

from lib.shared import Messages
from lib.signverify import Sign, Verify
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

        cfgc.gates_dir = cfg.app_dir + "/config/gates/"
        cfgc.spaces_dir = cfg.app_dir + "/config/spaces/"
        cfgc.providers_dir = cfg.app_dir + "/config/providers/"
        v = VDP(cfgc)
        v.save(cfg)

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
        ca = CertificateAuthority(ca_storage=cfg.ca_dir, common_name=cfg.ca_name)

    @staticmethod
    def provider(cfg):
        logging.getLogger("Wizard: Creating Provider IDs")
        ca = CertificateAuthority(ca_storage=cfg.ca_dir, common_name=cfg.ca_name)
        signing_key = nacl.signing.SigningKey.generate()
        verification_key = signing_key.verify_key

        # Step 2: Convert keys to bytes for storage
        signing_key_bytes = signing_key.encode(encoder=nacl.encoding.HexEncoder)
        verification_key_bytes = verification_key.encode(encoder=nacl.encoding.HexEncoder)

        with open(cfg.provider_private_key, 'wb') as private_key_file:
            private_key_file.write(signing_key_bytes)

        with open(cfg.provider_public_key, 'wb') as public_key_file:
            public_key_file.write(verification_key_bytes)

    @staticmethod
    def provider_vdp(cfg, providername="Easy LVPN provider", spacename="Free", wallet="[fill-in]", host="[fill-in]"):
        logging.getLogger("Wizard: Creating Provider VDP")
        with open(cfg.ca_dir + "/ca.crt", "r") as cf:
            cert = cf.read(-1)
        verification_key = Verify(cfg.provider_public_key).key()
        provider = {
            "filetype": "LetheanProvider",
            "version": "1.0",
            "providerid": verification_key,
            "name": providername,
            "description": providername,
            "ca": [cert],
            "wallet": "[example-wallet-address]",
            "manager-url": "https://[some-fqdn]:8790/",
            "spaces": [
                "free"
            ]
        }
        space = {
          "filetype": "LetheanSpace",
          "version": "1.0",
          "spaceid": "free",
          "providerid": verification_key,
          "name": spacename,
          "description": spacename,
          "price": {
            "per-day": 0
          }
        }
        httpgate = {
          "filetype": "LetheanGateway",
          "type": "http-proxy",
          "version": "1.0",
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
        vdp = VDP(cfg, vdpdata={
            "filetype": "VPNDescriptionProtocol",
            "version": "1.0",
            "providers": [provider],
            "gates": [httpgate],
            "spaces": [space]
        })
        vdp.save(cfg)

