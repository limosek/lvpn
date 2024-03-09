#!/bin/sh

set -e

# Build
docker build -t limosek/lvpn:dev .
echo "Build successful"

# No tests without args
if [ -z "$1" ]
then
  exit
fi

# Internal tests
docker run --sysctl net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN -ti limosek/lvpn:dev tests
echo "Internal tests successful"

# External tests
# Test SSH connect
docker run -d --name testssh --rm -p18080:8080 -p18124:8124 --sysctl net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN -ti limosek/lvpn:dev lvpnc -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --run-wallet=0 --run-gui=0 \
  --auto-connect="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-ssh/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"
while ! curl -q http://127.0.0.1:18124
do
  sleep 1
done

for i in 1 2 3 4 5 6; do
  curl -q http://127.0.0.1:18124/api/connections
  sleep 2
done

curl -q -x http://localhost:18080/ http://www.lthn
docker stop testssh

# Test WG connect
docker run --name testwg -d --rm -p18080:8080 -p18124:8124 --sysctl net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN -ti limosek/lvpn:dev lvpnc -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --run-wallet=0 --run-gui=0 \
  --auto-connect="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"
while ! curl -q http://127.0.0.1:18124
do
  sleep 1
done

for i in 1 2 3 4 5 6; do
  curl -q http://127.0.0.1:18124/api/connections
  sleep 2
done

docker stop testwg

# Test server
docker run --name testserver -d --rm -p18123:8123 --sysctl net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN -ti limosek/lvpn:dev lvpns -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --ignore-wg-key-mismatch=1 \
  --my-providers-dir=/usr/src/lvpn/config/providers --my-spaces-dir=/usr/src/lvpn/config/spaces --my-gates-dir=/usr/src/lvpn/config/gates
while ! curl -q http://127.0.0.1:18123
do
  sleep 1
done

# Try to run client to our server
docker run --name testwg -d --rm -p18124:8124 --link testserver --sysctl net.ipv6.conf.all.disable_ipv6=0 --cap-add=NET_ADMIN -ti limosek/lvpn:dev lvpnc -l INFO --manager-local-bind=0.0.0.0 --enable-wg=1 --run-wallet=0 --run-gui=0 \
  --force-manager-url=http://testserver:8123/ \
  --auto-connect="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"

while ! curl -q http://127.0.0.1:18124
do
  sleep 1
done

for i in 1 2 3 4 5 6; do
  curl -q http://127.0.0.1:18124/api/connections
  sleep 2
done

docker stop testwg testserver

echo "Tests finished"
