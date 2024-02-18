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

export WLS_CFG_DIR=$(realpath ./scfg)
export WLC_CFG_DIR=$(realpath ./ccfg)
export WLS_VAR_DIR=$(realpath ./svar)
export WLC_VAR_DIR=$(realpath ./cvar)

mkdir -p ./scfg ./ccfg ./svar ./cvar

python3 $PYTHONPATH/server.py --wallet-rpc-password=aaa > server.log 2>&1 &
python3 $PYTHONPATH/client.py > client.log 2>&1 &
sleep 5

python3 -m unittest ./api_server_session.py


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

export WLS_CFG_DIR=$(realpath ./scfg)
export WLC_CFG_DIR=$(realpath ./ccfg)
export WLS_VAR_DIR=$(realpath ./svar)
export WLC_VAR_DIR=$(realpath ./cvar)

mkdir -p ./scfg ./ccfg ./svar ./cvar




