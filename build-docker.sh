#!/bin/sh

docker build -t limosek/lvpn:dev .
docker run -ti limosek/lvpn:dev tests
