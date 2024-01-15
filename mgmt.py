import configargparse
import logging
import glob
import json
import nacl.signing
import nacl.encoding
import os
import sys
import time
from lib.signverify import Sign, Verify
from lib.vdp import VDP


def main():
    p = configargparse.ArgParser(default_config_files=['/etc/lthn/mgmt.conf'])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='Config file path', env_var='WLS_CONFIG')
    p.add_argument('-l', help='Log level', choices=['DEBUG', 'WARNING', 'ERROR'], default='WARNING',
                   env_var='WLS_LOGLEVEL')
    p.add_argument("--spaces-dir", help="Directory containing all spaces SDPs", default="/etc/lthn/spaces")
    p.add_argument("--gates-dir", help="Directory containing all gateway SDPs", default="/etc/lthn/gates")
    p.add_argument("--provider-private-key", help="Provider private key file", default="/etc/lthn/provider.private")
    p.add_argument("--provider-public-key", help="Provider public key file", default="/etc/lthn/provider.public")
    p.add_argument("cmd", help="Command to be used", type=str, choices={
        "generate-vdp": "Generate VDP from actual spaces and gates",
        "generate-provider": "Generate provider public and private keys",
        "sign-provider": "Sign provider as trusted by us",
        "verify-provider": "Verify signed provider"
    })
    p.add_argument("args", help="Args for command", nargs="*")

    cfg = p.parse_args()
    logging.basicConfig(level=cfg.l)

    if cfg.cmd == "generate-vdp":
        vdp = VDP(cfg)
        print(vdp.get_json())

    elif cfg.cmd == "generate-provider":

        # Step 1: Key generation
        signing_key = nacl.signing.SigningKey.generate()
        verification_key = signing_key.verify_key

        # Step 2: Convert keys to bytes for storage
        signing_key_bytes = signing_key.encode(encoder=nacl.encoding.HexEncoder)
        verification_key_bytes = verification_key.encode(encoder=nacl.encoding.HexEncoder)

        if os.path.exists(cfg.provider_private_key):
            logging.error("Private key %s already exists! Just generating IDs!" % cfg.provider_private_key)
        else:
            try:
                # Step 3: Save keys to files
                with open(cfg.provider_private_key, 'wb') as private_key_file:
                    private_key_file.write(signing_key_bytes)

                with open(cfg.provider_public_key, 'wb') as public_key_file:
                    public_key_file.write(verification_key_bytes)
            except Exception as e:
                logging.error("Cannot save provider files.")

        # Display the keys (optional)
        print(f"Private Key (NEVER SHARE THIS!): {signing_key_bytes.decode()}")
        print(f"Public Key: {verification_key_bytes.decode()}")

    elif cfg.cmd == "sign-provider":
        if cfg.args:
            providerid = cfg.args[0]
            tme = int(time.time())
            msg = "%s:%s" % (tme, providerid)
            logging.warning("Using provider %s and time %s (%s)" % (providerid, tme, msg))
            signed = Sign(cfg.provider_private_key).sign(msg)
            jsn = {
                "id": providerid,
                "time": tme,
                "hash": signed
            }
            print(json.dumps(jsn))

        else:
            logging.error("Need sign-provider providerid")
            sys.exit(1)

    elif cfg.cmd == "verify-provider":
        if cfg.args and len(cfg.args) == 1:
            jsn = json.loads(cfg.args[0])
            msg = "%s:%s" % (jsn["time"], jsn["id"])
            logging.warning("Using provider %s and time %s (%s)" % (jsn["id"], jsn["time"], msg))
            result = Verify(cfg.provider_public_key).verify(msg, jsn["hash"])
            if result:
                logging.warning("Signature OK")
                sys.exit()
            else:
                logging.warning("Signature Not valid.")
                sys.exit(1)
        else:
            logging.error("Need verify-provider 'JSON'")
            sys.exit(1)

    else:
        print("errr")
        sys.exit(1)


if __name__ == '__main__':
    main()

