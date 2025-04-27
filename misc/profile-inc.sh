
. /usr/src/lvpn/venv/bin/activate

export WLC_CFG_DIR=/home/lvpn/client/etc
export WLS_CFG_DIR=/home/lvpn/server/etc
export WLC_VAR_DIR=/home/lvpn/client/var
export WLS_VAR_DIR=/home/lvpn/server/var
export WLS_TMP_DIR=/tmp/lvpns
export WLC_TMP_DIR=/tmp/lvpnc
export NO_KIVY=1

lvpnc() {
  . /usr/src/lvpn/venv/bin/activate
  python3 /usr/src/lvpn/client.py "$@"
}

lvpns() {
  . /usr/src/lvpn/venv/bin/activate
  python3 /usr/src/lvpn/server.py "$@"
}

lmgmt() {
  . /usr/src/lvpn/venv/bin/activate
  python3 /usr/src/lvpn/mgmt.py "$@"
}
