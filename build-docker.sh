#!/bin/sh

docker build -t limosek/lvpn:dev .
docker run --cap-add=NET_ADMIN -ti limosek/lvpn:dev tests
