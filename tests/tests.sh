#!/bin/sh

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
python3 -m unittest ./runproc.py
python3 -m unittest ./sessions.py
python3 -m unittest ./connections.py

export WLS_CFG_DIR=$(realpath ./scfg)
export WLC_CFG_DIR=$(realpath ./ccfg)
export WLS_VAR_DIR=$(realpath ./svar)
export WLC_VAR_DIR=$(realpath ./cvar)

mkdir -p ./scfg ./ccfg ./svar ./cvar

python3 $PYTHONPATH/server.py &
python3 $PYTHONPATH/client.py --run-wallet=0 --run-gui=0 --auto-connect="" &

while ! curl -q http://127.0.0.1:8123
do
  sleep 1
done

while ! curl -q http://127.0.0.1:8124
do
  sleep 1
done

python3 -m unittest ./api_server_session.py
python3 -m unittest ./api_server_vdp.py
python3 -m unittest ./api_client_session.py
