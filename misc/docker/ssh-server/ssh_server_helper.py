#!/usr/bin/python3

import json
import logging
import logging.handlers
import random
import sys
from datetime import datetime
import socket
from sshkey_tools.cert import SSHCertificate


def find_random_free_port(max_iters=100, from_=20000, to_=50000):
    found = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    iters = 0
    while not found and iters < max_iters:
        try:
            port = random.randint(from_, to_)
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except socket.error as e:
            iters += 1


def authorized_principals(args):

    if len(args) != 4:
        sys.exit(1)
    else:
        user = args[1]
        tpe = args[2]
        crt = args[3]
        logging.error("%s %s %s" % (user, tpe, crt))
        sshcrt = SSHCertificate.from_string("%s %s" % (tpe, crt))
        if user in sshcrt.fields.principals.value and sshcrt.fields.key_id.value:
            now = datetime.now()
            if 0 and (sshcrt.fields.valid_after.value < now or sshcrt.fields.valid_before.value > now):
                sys.exit(3)
            else:
                jsn = {
                    "from": int(datetime.timestamp(sshcrt.fields.valid_after.value)),
                    "to": int(datetime.timestamp(sshcrt.fields.valid_before.value)),
                    "port1": find_random_free_port(),
                    "port2": find_random_free_port(),
                    "port3": find_random_free_port(),
                    "port4": find_random_free_port()
                }
                file = "/tmp/%s" % sshcrt.fields.valid_before.value
                with open(file, "w") as f:
                    f.write(json.dumps(jsn))
                print(sshcrt.fields.key_id.value)
        else:
            sys.exit(2)


def shell(args):
    pass

handler = logging.handlers.SysLogHandler(
    facility=logging.handlers.SysLogHandler.LOG_DAEMON,
    address='/dev/log'
    )
logging.getLogger().addHandler(handler)

if sys.argv[0].find("login") > 0:
    shell(sys.argv)
else:
    authorized_principals(sys.argv)
