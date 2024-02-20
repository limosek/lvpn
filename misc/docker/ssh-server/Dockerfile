FROM debian:bookworm

ARG USER=free-lvpn

RUN apt-get update && apt-get install -y ssh python3 python3-pip python3-venv
RUN useradd -p 1234 -m --home-dir /home/lvpn -s /bin/sshlogin $USER
RUN mkdir /run/sshd
RUN python3 -m venv /usr/local/lvpn
RUN . /usr/local/lvpn/bin/activate; pip3 install sshkey-tools

COPY ./sshlogin /bin/sshlogin
RUN chmod +x /bin/sshlogin

COPY ./authorized_principals.sh /bin/
RUN chmod +x /bin/authorized_principals.sh

COPY ./ssh_server_helper.py /bin/ssh_server_helper.py
RUN chmod +x /bin/

VOLUME /etc/ssh

EXPOSE 2222

ENTRYPOINT ["/usr/sbin/sshd", "-D"]
