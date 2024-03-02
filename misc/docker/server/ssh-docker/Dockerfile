FROM debian:bookworm

RUN apt-get update && apt-get install -y ssh net-tools

RUN useradd -p 1234 -m --home-dir /home/lvpn -s /bin/sshlogin lvpn
RUN mkdir /run/sshd
COPY ./sshlogin /bin/sshlogin
RUN chmod +x /bin/sshlogin

VOLUME /etc/ssh

EXPOSE 2222

ENTRYPOINT ["/usr/sbin/sshd", "-D"]
