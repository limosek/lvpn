#!/bin/sh

set -e
cd /home/lvpn/src
. venv/bin/activate

case $1 in

client)
  shift
  python3 client.py "$@"
  ;;

server)
  shift
  python3 client.py "$@"
  ;;

sh)
  bash
  ;;

*)
  echo "Use client|server|sh"
  exit 1
  ;;

esac
