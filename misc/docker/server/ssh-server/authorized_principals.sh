#!/bin/sh

. /usr/local/lvpn/bin/activate

exec python3 /bin/ssh_server_helper.py "$@"
