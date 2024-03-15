#!/bin/sh

. /etc/profile

haproxy_cfg(){
  cat /home/lvpn/server/etc/ca/certs/localhost/*.pem /home/lvpn/server/etc/ca/certs/localhost/*.crt >/home/lvpn/server/etc/ca-combined.pem
  cp /home/lvpn/server/etc/ca/ca.crt /home/lvpn/server/etc/ca.crt
  cat >/home/lvpn/server/etc/haproxy.cfg <<EOF
global
        daemon

        ssl-default-bind-ciphers TLS13-AES-256-GCM-SHA384:TLS13-AES-128-GCM-SHA256:TLS13-CHACHA20-POLY1305-SHA256:EECDH+AESGCM:EECDH+CHACHA20
        ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

defaults
        log     global
        mode    tcp
        option  dontlognull

        timeout connect 5000
        timeout client  600000
        timeout server  600000
        timeout tunnel  0
        option                  http-keep-alive
        http-reuse              safe

frontend authenticated-tls-proxy
    bind 0.0.0.0:8880 ssl crt /home/lvpn/server/etc/ca-combined.pem ca-file /home/lvpn/server/etc/ca.crt verify required tfo
    default_backend http-proxy

frontend manager-tls-proxy
    bind 0.0.0.0:8881 ssl crt /home/lvpn/server/etc/ca-combined.pem ca-file /home/lvpn/server/etc/ca.crt verify none tfo
    default_backend manager

backend http-proxy
    mode http
    # Must be directed to your HTTP proxy instance
    server localproxy 127.0.0.1:8888

backend manager
    mode http
    # Must be directed to your lvpns manager
    server localproxy 127.0.0.1:8123
EOF
}

tinyproxy_cfg(){
  cat >/home/lvpn/server/etc/tinyproxy.cfg <<EOF
Port 8888
Syslog Yes
LogLevel Warning
PidFile "/tmp/tinyproxy.pid"
XTinyproxy Yes
MaxClients 100
PidFile "/tmp/tinyproxy.pid"
DisableViaHeader On
Allow 100.64.0.0/10
ConnectPort 443
ConnectPort 8080
EOF
}

mkdir -p "$WLS_TMP_DIR" "$WLC_TMP_DIR" "$WLC_CFG_DIR" "$WLC_VAR_DIR" "$WLS_VAR_DIR" "$WLS_CFG_DIR"

if [ -n "$DAEMON_HOST" ]
then
  CARGS="--daemon-host $DAEMON_HOST"
fi

if [ -z "$LVPNC_ARGS" ]
then
  LVPNC_ARGS="--enable-wg=1 --wg-cmd-prefix=sudo --local-bind=0.0.0.0 --manager-local-bind=0.0.0.0 --wg-shutdown-on-disconnect=0"
fi

if [ -z "$LVPNS_ARGS" ]
then
  LVPNS_ARGS="--enable-wg=1 --wg-cmd-prefix=sudo --manager-local-bind=0.0.0.0 "
fi

if [ -z "$DAEMON_ARGS" ]
then
  DAEMON_ARGS="--non-interactive --confirm-external-bind --data-dir=/home/lvpn/blockchain \
      --p2p-bind-ip=0.0.0.0 --rpc-bind-ip=0.0.0.0 --log-level=0 --restricted-rpc --add-exclusive-node 172.31.129.19 --add-priority-node 172.31.129.19 --add-peer 172.31.129.19"
fi

# Main logic here
case $1 in

client|lvpnc)
  shift
  echo "Starting client:" lvpnc $LVPNC_ARGS $CARGS "$@"
  lvpnc $LVPNC_ARGS $CARGS "$@"
  ;;

server|lvpns)
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

  # Run local daemon
  echo "Running local daemon"
  while true;
  do
    letheand $DAEMON_ARGS >/home/lvpn/daemon.log 2>&1
    sleep 5
  done &

  # Wait for daemon to start
  echo "Waiting for daemon to start."
  while ! curl -q http://127.0.0.1:48782/json_rpc 2>/dev/null >/dev/null
  do
    sleep 1
    echo "."
  done
  echo OK

  while true
  do
    if [ -f $WLS_CFG_DIR/wallet_pass ]
    then
      export EASY_WALLET_PASSWORD=$(cat $WLS_CFG_DIR/wallet_pass)
      export EASY_WALLET_RPC_PASSWORD=$(cat $WLS_CFG_DIR/wallet_rpc_pass)
    fi
    # First, let us start client
    $0 lvpnc $LVPNC_ARGS --run-wallet=0 --run-gui=0 --auto-reconnect=20 --auto-pay-days=30 \
      --wallet-rpc-url=http://localhost:1444/json_rpc --wallet-rpc-password="$EASY_WALLET_RPC_PASSWORD" \
      --wallet-password="$EASY_WALLET_PASSWORD" --wallet-name=vpn-wallet \
      --daemon-rpc-url="http://172.31.129.19:48782/json_rpc" --daemon-host="172.31.129.19" \
      --auto-connect=${NODE_AUTO_CONNECT} >/home/lvpn/client.log 2>&1
    sleep 10
  done &

  # Wait for client to connect
  echo "Waiting for lvpnc to connect."
  while ! curl -q http://127.0.0.1:8124/api/connections 2>/dev/null | grep endpoint >/dev/null
  do
    sleep 1
    echo "."
  done
  echo OK

  # Wait for client to have wg session
  echo "Waiting for working WG session."
  while ! curl -q http://127.0.0.1:8124/api/sessions 2>/dev/null | grep client_ipv4_address >/dev/null
  do
    sleep 1
    echo "."
  done
  IP=$(curl -q http://localhost:8124/api/sessions | json_pp | grep client_ipv4_address | cut -d '"' -f 4)
  echo "OK (IP=$IP)"

  # Generate VDP
  if ! [ -f "$WLS_CFG_DIR"/provider.private ]
  then
    echo "Running easy-provider"
    export EASY_WALLET_PASSWORD=$(pwgen 12)
    export EASY_WALLET_RPC_PASSWORD=$(pwgen 12)
    export EASY_ENDPOINT=$IP
    rm -rf /home/lvpn/easy
    $0 easy-provider
    cp -R /home/lvpn/easy/* "$WLS_CFG_DIR"/
    # Configure haproxy
    haproxy_cfg
    # Configure tinyproxy
    tinyproxy_cfg
  else
    export EASY_WALLET_PASSWORD=$(cat $WLS_CFG_DIR/wallet_pass)
    export EASY_WALLET_RPC_PASSWORD=$(cat $WLS_CFG_DIR/wallet_rpc_pass)
  fi

  # Remove stale files which blocks wallets to start
  rm -f /tmp/*.login

  # Run client wallet
  echo "Running client wallet"
  while true;
  do
    cd /tmp && lethean-wallet-rpc --wallet-dir="$WLS_CFG_DIR" --rpc-login="vpn:$EASY_WALLET_RPC_PASSWORD" \
      --rpc-bind-port=1444 --trusted-daemon >/home/lvpn/client-wallet.log 2>&1
    sleep 5
  done &

  # Run server wallet
  echo "Running server wallet"
  while true;
  do
    cd /tmp && lethean-wallet-rpc --wallet-file="$WLS_CFG_DIR"/vpn-wallet --rpc-login="vpn:$EASY_WALLET_RPC_PASSWORD" \
      --rpc-bind-port=1445 --trusted-daemon --password "$EASY_WALLET_PASSWORD" >/home/lvpn/server-wallet.log 2>&1
    sleep 5
  done &

  # Wait for client wallet
  echo "Waiting for client wallet."
  while ! curl -q http://localhost:1444/json_rpc 2>/dev/null >/dev/null
  do
    sleep 1
    echo "."
  done
  echo "OK"

  # Wait for client wallet
  echo "Waiting for server wallet."
  while ! curl -q http://localhost:1445/json_rpc 2>/dev/null >/dev/null
  do
    sleep 1
    echo "."
  done
  echo "OK"

  # Run the server
  echo "Running server"
  while true
  do
    $0 lvpns $LVPNS_ARGS \
      --wallet-rpc-url=http://localhost:1445/json_rpc --wallet-rpc-password="$EASY_WALLET_RPC_PASSWORD" >/home/lvpn/server.log 2>&1
    sleep 10
  done &

  # Regularly Push new VDP to server and fetch fresh VDP
  while true
  do
    # Refresh VDP timestamps
    $0 lmgmt refresh-vdp
    # Push our VDP
    $0 lmgmt push-vdp 94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091 || true
    # Fetch fresh VDP from main server for client and server
    $0 lmgmt fetch-vdp 94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091 || true
    WLC_CLIENT=1 $0 lmgmt fetch-vdp 94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091 || true
    sleep 3500
  done &

  if [ "${NODE_RUN_SERVER}" = "yes" ]
  then
    echo "Running haproxy"
    /usr/sbin/haproxy -f /home/lvpn/server/etc/haproxy.cfg
    echo "Running tinyproxy"
    tinyproxy -c /home/lvpn/server/etc/tinyproxy.cfg
  fi

  if [ "${NODE_RUN_SHARE}" = "yes" ] && [ -d "${NODE_SHARE_DIR}" ]
  then
    echo "Running ctorrent"
    rm -f ${NODE_SHARE_DIR}/node.torrent
    cd ${NODE_SHARE_DIR} && ctorrent -t -u "${NODE_TRACKER_URL}" -s "node.torrent" ./
    ctorrent -p 2706 -d node.torrent
  else
    echo "Sharing files disabled"
  fi

  echo "Everythig UP! Great!"
  # Wait for background processes
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
  ;;
  esac

esac
