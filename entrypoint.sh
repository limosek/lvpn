#!/bin/sh

set -e
cd /home/lvpn/src
. venv/bin/activate

export WLC_VAR_DIR=/home/lvpn
export WLS_VAR_DIR=/home/lvpn

case $1 in

client|lvpnc)
  shift
  python3 client.py $LVPNC_ARGS "$@"
  ;;

server|lvpns)
  shift
  python3 server.py $LVPNS_ARGS "$@"
  ;;

mgmt)
  shift
  python3 mgmt.py "$@"
  ;;

sh)
  bash
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

  echo "Use client|server|sh"
  exit 1
  ;;

esac
