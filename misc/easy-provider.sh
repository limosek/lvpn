#!/bin/sh

if [ -z "$LMGMT" ]
then
  LMGMT="lmgmt"
fi

mgmt() {
  echo lmgmt "$@"
  $LMGMT "$@"
}

generate_ssh_ca() {
  ssh-keygen -t ecdsa -f "$WLS_CFG_DIR/ssh-user-ca" -C "Easy-$(cat $WLS_CFG_DIR/provider.public)" -N ""
  ssh-keygen -t ecdsa -f "$WLS_CFG_DIR/ssh-host-ca" -C "Easy-$(cat $WLS_CFG_DIR/provider.public)" -N ""
  ssh-keygen -s "$WLS_CFG_DIR/ssh-host-ca" -I $EASY_FQDN -h -n $EASY_FQDN -V +352w "$WLS_CFG_DIR/ssh-host-ca.pub"
}

generate_wallet() {
  lethean-wallet-cli --generate-new-wallet "$1" \
            --daemon-address=seed.lethean.io:48782 \
            --log-level=1 \
            --mnemonic-language=English \
            --trusted-daemon \
            --password "$2" \
            rescan_bc </dev/null &
  sleep 10
}

set -e

## Test empty directory
if [ -z "$WLS_CFG_DIR" ] || [ -d "$WLS_CFG_DIR" ]
then
  echo "You need to set env variable WLS_CFG_DIR to non-existing directory which will be created automatically."
  exit 1
fi

if ! which pwgen >/dev/null
then
  echo "You need pwgen binary"
  exit 1
fi

mkdir "$WLS_CFG_DIR"

if [ -z "$EASY_WALLET_PASSWORD" ]
then
  EASY_WALLET_PASSWORD=$(pwgen 12)
  echo "VPN password: $EASY_WALLET_PASSWORD"
fi
echo $EASY_WALLET_PASSWORD >$WLS_CFG_DIR/wallet_pass

if [ -z "$EASY_WALLET_RPC_PASSWORD" ]
then
  EASY_WALLET_RPC_PASSWORD=$(pwgen 12)
  echo "VPN RPC password: $EASY_WALLET_RPC_PASSWORD"
fi
echo $EASY_WALLET_RPC_PASSWORD >$WLS_CFG_DIR/wallet_rpc_pass

if ! which lethean-wallet-cli >/dev/null
then
  echo "You need lethean-wallet-cli binary"
  exit 1
fi

mgmt init

## Generate provider keys
mgmt generate-provider-keys
chmod 700 "$WLS_CFG_DIR/provider.private"

## Generate CA
if [ -z "$EASY_CA_CN" ]
then
  EASY_CA_CN="Easy-provider-$(cat $WLS_CFG_DIR/provider.public)"
fi
if [ -z "$EASY_FQDN" ]
then
  EASY_FQDN="vpn.$(cat $WLS_CFG_DIR/provider.public).lthn"
fi

if [ -z "$EASY_DAYS" ]
then
  EASY_DAYS="825"
fi
mgmt generate-ca "$EASY_CA_CN" $EASY_DAYS
mgmt issue-crt "$EASY_FQDN" 365

## Generate SSH CA
generate_ssh_ca

## Generate wallet
generate_wallet "$WLS_CFG_DIR/vpn-wallet" "$EASY_WALLET_PASSWORD" >/dev/null 2>/dev/null

# Generate VDP
mkdir -p $WLS_CFG_DIR/gates $WLS_CFG_DIR/providers $WLS_CFG_DIR/spaces
mgmt generate-vdp "$EASY_CA_CN" free "$EASY_ENDPOINT" "$(cat $WLS_CFG_DIR/vpn-wallet.address.txt)" http://$EASY_ENDPOINT:8123

echo "Waiting for Wallet process to finish"
wait
