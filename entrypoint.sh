#!/bin/sh

set -e

. /etc/profile

mkdir -p "$WLS_TMP_DIR" "$WLC_TMP_DIR" "$WLC_CFG_DIR" "$WLC_VAR_DIR" "$WLS_VAR_DIR"

if [ -n "$DAEMON_HOST" ]
then
  CARGS="--daemon-host $DAEMON_HOST"
fi

case $1 in

client|lvpnc)
  mkdir -p "$WLC_CFG_DIR"
  shift
  echo "Starting client:" lvpnc $LVPNC_ARGS $CARGS --local-bind=0.0.0.0 --manager-local-bind=0.0.0.0 "$@"
  lvpnc $LVPNC_ARGS $ARGS $CARGS --enable-wg=1 --wg-cmd-prefix=sudo --local-bind=0.0.0.0 --manager-local-bind=0.0.0.0 "$@"
  ;;

server|lvpns)
  mkdir -p "$WLS_CFG_DIR"
  shift
  echo "Starting server:" lvpns $LVPNS_ARGS --enable-wg=1 --wg-cmd-prefix=sudo --manager-local-bind=0.0.0.0 "$@"
  lvpns --enable-wg=1 --wg-cmd-prefix=sudo --manager-local-bind=0.0.0.0 $LVPNS_ARGS "$@"
  ;;

mgmt|lmgmt)
  shift
  lmgmt "$@"
  ;;

easy-provider)
  shift
  echo "Generating new provider to /home/lvpn/easy."
  echo "You can tune this wizard by setting variables"
  echo "EASY_FQDN - FQDN or IP of your provider"
  echo "EASY_CA_CN - CN for generated CA"
  if [ -z "$EASY_FQDN" ]
  then
    export EASY_FQDN=localhost
  fi
  WLS_CFG_DIR=/home/lvpn/easy LMGMT="/usr/src/lvpn/venv/bin/python3 /usr/src/lvpn/mgmt.py" easy-provider.sh "$@"
  echo "Do not forget to save /home/lvpn/easy directory!"
  ;;

tests)
  shift
  cp -R /usr/src/lvpn/tests/ /tmp/tests
  cd /tmp/tests
  sudo ./tests.sh /usr/src/lvpn
  $0 easy-provider
  echo "========================================================"
  echo "Easy provider test passed"
  echo "========================================================"
  ;;

set-perms)
  chown -R lvpn:lvpn /home/lvpn
  ;;

sh)
  shift
  bash --init-file /etc/profile "$@"
  ;;

*)
  if [ "$MODE" = "server" ];
  then
    exec $0 server "$@"
  else
      exec $0 client "$@"
  fi

  echo "Use client|server|mgmt|set-perms|easy-provider|sh"
  exit 1
  ;;

esac
