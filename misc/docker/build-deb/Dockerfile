FROM debian:bookworm
MAINTAINER Limos <lukas@macura.cz>

LABEL description="LVPN"

RUN apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y devscripts debianutils \
      python3 python3-virtualenv python3-pip dh-virtualenv

RUN apt-get install -y python3-kivy python3-sdl2 wget

RUN apt-get install -y libxau6 libjpeg62-turbo libwebp7

RUN apt-get install -y python3-cryptography python3-nacl python3-socks python3-paramiko python3-urllib3 python3-flask python3-sshtunnel python3-stripe python3-jsonschema python3-icmplib python3-requests python3-dnspython

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
COPY ./debian/ /usr/src/lvpn/debian/

WORKDIR /usr/src/lvpn/

RUN dh binary --with python-virtualenv --use-system-packages


