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

unittest(){
  echo python3 -m unittest $1 >&2
  if python3 -m unittest $1 >$1.log 2>&1
  then
    echo "OK"
  else
    cat $1.log
    cat server.log || true
    cat client.log || true
    echo "ERROR"
    exit 1
  fi
}

unittest ./vdp.py
unittest ./sessions.py
unittest ./connection.py
unittest ./wg_engine.py
unittest ./wg_service.py
#unittest ./proxies.py

export WLS_CFG_DIR=$(realpath ./scfg)
export WLC_CFG_DIR=$(realpath ./ccfg)
export WLS_VAR_DIR=$(realpath ./svar)
export WLC_VAR_DIR=$(realpath ./cvar)

mkdir -p ./scfg ./ccfg ./svar ./cvar
cp -R $PYTHONPATH/config/* ./scfg/

echo $PYTHONPATH/server.py >&2
python3 $PYTHONPATH/server.py --ignore-wg-key-mismatch=1 --manager-local-bind=0.0.0.0 --enable-wg=1 -l INFO >server.log 2>&1 &
SPID=$!
echo "Server PID: $SPID"
while ! curl -q http://127.0.0.1:8123
do
  sleep 1
done

echo $PYTHONPATH/client.py >&2
python3 $PYTHONPATH/client.py -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --force-manager-url=http://127.0.0.1:8123/ --run-wallet=0 --run-gui=0 --auto-connect="" >client.log 2>&1  &
CPID=$!
echo "Client PID: $CPID"
while ! curl -q http://127.0.0.1:8124
do
  sleep 1
done

unittest ./api_server_session.py
unittest ./api_server_vdp.py
unittest ./api_client_session.py

if ! kill $CPID
then
  cat client.log
  exit 2
fi
if ! kill $SPID
then
  cat server.log
  exit 2
fi

echo "========================================================"
echo "Unit tests passed"
echo "========================================================"
