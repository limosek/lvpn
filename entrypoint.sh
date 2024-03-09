#!/bin/sh

set -e

. /etc/profile

mkdir -p "$WLS_TMP_DIR" "$WLC_TMP_DIR" "$WLC_CFG_DIR" "$WLC_VAR_DIR" "$WLS_VAR_DIR"

if [ -n "$DAEMON_HOST" ]
then
  CARGS="--daemon-host $DAEMON_HOST"
fi

if [ -z "$LVPNC_ARGS" ]
then
  LVPNC_ARGS="--enable-wg=1 --wg-cmd-prefix=sudo --local-bind=0.0.0.0 --manager-local-bind=0.0.0.0"
fi

if [ -z "$LVPNS_ARGS" ]
then
  LVPNS_ARGS="--enable-wg=1 --wg-cmd-prefix=sudo --manager-local-bind=0.0.0.0 "
fi

case $1 in

client|lvpnc)
  mkdir -p "$WLC_CFG_DIR"
  shift
  echo "Starting client:" lvpnc $LVPNC_ARGS $CARGS "$@"
  lvpnc $LVPNC_ARGS $CARGS "$@"
  ;;

server|lvpns)
  mkdir -p "$WLS_CFG_DIR"
  shift
  echo "Starting server:" lvpns $LVPNS_ARGS "$@"
  lvpns $LVPNS_ARGS "$@"
  ;;

mgmt|lmgmt)
  shift
  lmgmt "$@"
  ;;

node)
  if ! [ -d /home/lvpn/blockchain ]
  then
    mkdir /home/lvpn/blockchain
  fi
  $0 set-perms
  if ! [ -f "$WLS_CFG_DIR"/provider.private ]
  then
    $0 easy-provider
    cp -R /home/lvpn/easy/* "$WLS_CFG_DIR"/
  fi
  lethean-wallet-rpc --wallet-dir="$WLS_CFG_DIR" --rpc-login="vpn:$(cat $WLS_CFG_DIR/wallet_rpc_pass)" \
    --rpc-bind-port=1444 --daemon-address=172.31.129.19:48782 --trusted-daemon &
  $0 lvpns $LVPNS_ARGS &
  $0 lvpnc $LVPNC_ARGS --run-wallet=0 --run-gui=0 \
    --wallet-rpc-url=http://localhost:1444/json_rpc --wallet-rpc-password="$(cat $WLS_CFG_DIR/wallet_rpc_pass)" \
    --wallet-password="$(cat $WLS_CFG_DIR/wallet_pass)" --wallet-name=vpn-wallet \
    --daemon-rpc-url="http://172.31.129.19:48782/json_rpc" --daemon-host="172.31.129.19" \
    --auto-connect="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free" &
  letheand --non-interactive --confirm-external-bind --data-dir=/home/lvpn/blockchain \
    --p2p-bind-ip=0.0.0.0 --rpc-bind-ip=0.0.0.0 --log-level=0 --restricted-rpc --add-peer 172.31.129.19 &
  wait
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
  sudo mkdir -p "$WLS_TMP_DIR" "$WLC_TMP_DIR" "$WLC_CFG_DIR" "$WLC_VAR_DIR" "$WLS_VAR_DIR"
  sudo chown -R lvpn:lvpn /home/lvpn
  ;;

sh)
  shift
  bash --init-file /etc/profile "$@"
  ;;

*)
  case $MODE in
"server")
   $0 server "$@"
   ;;
"client")
  $0 client "$@"
  ;;
"node")
  $0 node "$@"
  ;;
*)
  echo "Use client|server|node|mgmt|set-perms|easy-provider|sh"
  exit 1
  esac
  ;;

esac
