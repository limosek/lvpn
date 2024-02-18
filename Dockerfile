FROM python:3.11-bookworm
MAINTAINER Limos <lukas@macura.cz>

LABEL version="1.0"
LABEL description="LVPN"

RUN apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y sudo joe less net-tools wget python3-venv pwgen;

ARG DAEMON_BIN_URL="https://github.com/letheanVPN/blockchain-iz/releases/latest/download/lethean-cli-linux.tar"

ENV LVPNC_ARGS=""
ENV LVPNS_ARGS=""
ENV MODE="client"
ENV EASY_FQDN=""
ENV EASY_CA_CN=""
ENV EASY_CA_DAYS=""
ENV MODE="client"

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
COPY tests/* /tmp/tests/
COPY tests/* /usr/src/lvpn/tests/
COPY ./entrypoint.sh /

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

RUN PYTHONPATH=/usr/src/lvpn /tmp/tests/tests.sh

RUN rm -rf /home/lvpn/server /home/lvpn/client /tmp/*

ENTRYPOINT ["/entrypoint.sh"]
CMD ["client"]
