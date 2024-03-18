FROM python:3.11-bookworm
MAINTAINER Limos <lukas@macura.cz>

LABEL version="1.0"
LABEL description="LVPN"

RUN apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y sudo joe less net-tools wget python3-venv pwgen wireguard-tools wireguard-go iproute2 iputils-ping tcpdump iptables tinyproxy haproxy stunnel ctorrent sqlite3;

ARG DAEMON_BIN_URL="https://github.com/letheanVPN/blockchain-iz/releases/latest/download/lethean-cli-linux.tar"

ENV LVPNC_ARGS=""
ENV LVPNS_ARGS=""
ENV MODE="client"
ENV EASY_FQDN=""
ENV EASY_CA_CN=""
ENV EASY_CA_DAYS=""
ENV MODE="client"
ENV DAEMON_HOST="seed.lethean.io"
ENV HTTP_PROXY=""
ENV DAEMON_ARGS=""
ENV NODE_AUTO_CONNECT="94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free-wg/94ece0b789b1031e0e285a7439205942eb8cb74b4df7c9854c0874bd3d8cd091.free"
ENV NODE_RUN_SERVER="yes"
ENV NODE_SHARE_DIR="/home/lvpn/share"
ENV NODE_TRACKER_URL="http://172.31.111.19:6969/announce"
ENV NODE_RUN_SHARE="yes"

# Client wallet RPC
EXPOSE 1444
# Server wallet RPC
EXPOSE 1445
# Client MGMT
EXPOSE 8123
# Server MGMT
EXPOSE 8124
# Client HTTP Proxy
EXPOSE 8080
# Client Socks Proxy
EXPOSE 8081
# Daemon P2P
EXPOSE 48772
# Daemon RPC
EXPOSE 48782
# Easy-http-tls-proxy
EXPOSE 8880
# Easy-tls-manager
EXPOSE 8881
# Torent
EXPOSE 2706

RUN useradd -ms /bin/bash lvpn; \
  echo "lvpn ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers; \
  mkdir /usr/src/lvpn; chown -R lvpn /usr/src/lvpn

VOLUME /home/lvpn

COPY client/* /usr/src/lvpn/client/
COPY server/* /usr/src/lvpn/server/
COPY lib/* /usr/src/lvpn/lib/
COPY config/ /usr/src/lvpn/config/
COPY misc/ /usr/src/lvpn/misc/
COPY misc/easy-provider.sh /usr/local/bin/
COPY server.py client.py setup.cfg setup.py mgmt.py /usr/src/lvpn/
COPY requirements.txt /usr/src/lvpn/
COPY requirements-lite.txt /usr/src/lvpn/
COPY build/* /usr/src/lvpn/build/
COPY tests/* /usr/src/lvpn/tests/
COPY ./entrypoint.sh /
COPY ./misc/profile-inc.sh /etc/profile.d/lvpn.sh

WORKDIR /usr/src/lvpn/build/
RUN wget -nc -c $DAEMON_BIN_URL
RUN mkdir -p /usr/src/lvpn/bin/ && tar -xf $(basename $DAEMON_BIN_URL) -C /usr/local/bin/

RUN chown -R lvpn /home/lvpn /tmp

WORKDIR /usr/src/lvpn/
USER lvpn

RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip3 install -r requirements-lite.txt

RUN ./misc/combine-openapi-files.sh

WORKDIR /home/lvpn

RUN /entrypoint.sh lvpnc -h
RUN /entrypoint.sh lvpns -h
RUN /entrypoint.sh lmgmt -h
RUN /entrypoint.sh lmgmt list-providers

ENTRYPOINT ["/entrypoint.sh"]
CMD [""]
