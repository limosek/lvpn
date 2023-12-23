FROM python:3.11-bookworm
MAINTAINER Limos <lukas@macura.cz>

LABEL version="1.0"
LABEL description="LVPN"

RUN apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y sudo joe less net-tools wget python3-venv;

ARG DAEMON_BIN_URL="https://github.com/letheanVPN/blockchain-iz/releases/latest/download/lethean-cli-linux.tar"
ARG DAEMON_HOST="seed.lethean.io"

ENV DAEMON_HOST="$DAEMON_HOST"

RUN useradd -ms /bin/bash lvpn; \
  echo "lvpn ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers; \
  mkdir /home/lvpn/app;

COPY lvpn/client/* /home/lvpn/src/client/
COPY lvpn/server/* /home/lvpn/src/server/
COPY lvpn/lib/* /home/lvpn/src/lib/
COPY config/ /home/lvpn/src/config/
COPY lvpn/server.py client.py setup.cfg setup.py /home/lvpn/src/
COPY build-msi.cmd /home/lvpn/src/

RUN wget -nc -c $DAEMON_BIN_URL
RUN mkdir -p /home/lvpn/src/bin/ && tar -xf $(basename $DAEMON_BIN_URL) -C /home/lvpn/src/bin/

RUN chown -R lvpn /home/lvpn

WORKDIR /home/lvpn/src
USER lvpn

RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip3 install -r requirements.txt && \
    python3 client.py -h && \
    python3 server.py -h

COPY ./entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["client"]


