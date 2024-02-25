#!/bin/sh

if [ -n "$1" ]
then
  export PYTHONPATH=$1
fi

set -e

cd $(dirname $0)
if [ -z "$PYTHONPATH" ]
then
  export PYTHONPATH=$(pwd)/..
fi
if [ -f $PYTHONPATH/venv/bin/activate ]
then
  . $PYTHONPATH/venv/bin/activate
fi

python3 -m unittest ./vdp.py
python3 -m unittest ./sessions.py
python3 -m unittest ./connection.py
python3 -m unittest ./wg_engine.py
python3 -m unittest ./wg_service.py

export WLS_CFG_DIR=$(realpath ./scfg)
export WLC_CFG_DIR=$(realpath ./ccfg)
export WLS_VAR_DIR=$(realpath ./svar)
export WLC_VAR_DIR=$(realpath ./cvar)

mkdir -p ./scfg ./ccfg ./svar ./cvar
cp -R $PYTHONPATH/config/* ./scfg/

python3 $PYTHONPATH/server.py --manager-local-bind=0.0.0.0 --enable-wg=1 -l INFO --my-providers-dir=$PYTHONPATH/config/providers --my-spaces-dir=$PYTHONPATH/config/spaces --my-gates-dir=$PYTHONPATH/config/gates &
while ! curl -q http://127.0.0.1:8123
do
  sleep 1
done

python3 $PYTHONPATH/client.py -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --force-manager-url=http://127.0.0.1:8123/ --run-wallet=0 --run-gui=0 --auto-connect="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free" &
while ! curl -q http://127.0.0.1:8124
do
  sleep 1
done

python3 -m unittest ./api_server_session.py
python3 -m unittest ./api_server_vdp.py
python3 -m unittest ./api_client_session.py

# Test that autoconnect works
curl -q -x http://localhost:8080/ http://www.lthn >/dev/null

killall python3
sleep 7

EASY_FQDN=a.b.c.d WLS_CFG_DIR=/home/lvpn/easy LMGMT="/usr/src/lvpn/venv/bin/python3 /usr/src/lvpn/mgmt.py" easy-provider.sh "$@"

