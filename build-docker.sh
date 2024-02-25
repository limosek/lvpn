#!/bin/sh

set -e

docker build -t limosek/lvpn:dev .
docker run --cap-add=NET_ADMIN -ti limosek/lvpn:dev tests

echo "Build successful"
