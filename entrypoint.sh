#!/bin/sh

set -e
. /usr/src/lvpn/venv/bin/activate

export WLC_CFG_DIR=/home/lvpn/client/etc
export WLS_CFG_DIR=/home/lvpn/server/etc
export WLC_VAR_DIR=/home/lvpn/client/var
export WLS_VAR_DIR=/home/lvpn/server/var
export WLS_TMP_DIR=/tmp/lvpns
export WLC_TMP_DIR=/tmp/lvpnc
export NO_KIVY=1

mkdir -p "$WLS_TMP_DIR" "$WLC_TMP_DIR" "$WLC_CFG_DIR" "$WLC_VAR_DIR" "$WLS_VAR_DIR"

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

case $1 in

client|lvpnc)
  shift
  lvpnc $LVPNC_ARGS "$@"
  ;;

server|lvpns)
  mkdir -p "$WLS_CFG_DIR"
  shift
  lvpns --manager-local-bind=0.0.0.0 $LVPNS_ARGS "$@"
  ;;

mgmt)
  shift
  mgmt "$@"
  ;;

easy-provider)
  shift
  LMGMT="/usr/src/lvpn/venv/bin/python3 /usr/src/lvpn/mgmt.py" easy-provider.sh "$@"
  ;;

sh)
  shift
  bash "$@"
  ;;

*)
  if [ "$MODE" = "server" ];
  then
    exec $0 server "$@"
  fi
  if [ "$MODE" = "client" ];
  then
    exec $0 client "$@"
  fi

  echo "Use client|server|easy-provider|sh"
  exit 1
  ;;

esac
