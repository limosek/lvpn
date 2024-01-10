FROM python:3.11-bookworm
MAINTAINER Limos <lukas@macura.cz>

LABEL version="1.0"
LABEL description="LVPN"

RUN apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y sudo joe less net-tools wget python3-venv;

ARG DAEMON_BIN_URL="https://github.com/letheanVPN/blockchain-iz/releases/latest/download/lethean-cli-linux.tar"

ENV LVPNC_ARGS=""
ENV LVPNS_ARGS=""
ENV MODE="client"

RUN useradd -ms /bin/bash lvpn; \
  echo "lvpn ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers; \
  mkdir /home/lvpn/app;

COPY client/* /home/lvpn/src/client/
COPY server/* /home/lvpn/src/server/
COPY lib/* /home/lvpn/src/lib/
COPY config/ /home/lvpn/src/config/
COPY server.py client.py setup.cfg setup.py /home/lvpn/src/
COPY requirements.txt /home/lvpn/src/
COPY requirements-lite.txt /home/lvpn/src/
COPY build/* /home/lvpn/src/build/
COPY ./entrypoint.sh /

WORKDIR /home/lvpn/src/build/
RUN wget -nc -c $DAEMON_BIN_URL
RUN mkdir -p /home/lvpn/src/bin/ && tar -xf $(basename $DAEMON_BIN_URL) -C /home/lvpn/src/bin/

RUN chown -R lvpn /home/lvpn

WORKDIR /home/lvpn/src
USER lvpn

RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip3 install -r requirements-lite.txt

RUN . venv/bin/activate && python client.py -h
RUN . venv/bin/activate && python server.py -h

ENTRYPOINT ["/entrypoint.sh"]
CMD ["client"]


