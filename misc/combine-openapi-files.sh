#!/bin/sh

export sdir=$(dirname $0)/schemas/

(
cat $sdir/client-api.yaml
for f in "provider" "gate" "space" "session" "vdp" "connection";
do
  cat $sdir/$f.yaml
done
) > $sdir/client.yaml

(
cat $sdir/server-api.yaml
for f in "provider" "gate" "space" "session" "vdp";
do
  cat $sdir/$f.yaml
done
) > $sdir/server.yaml
