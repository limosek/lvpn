import logging
import socket
import ssl
import threading
import time
from copy import copy

import setproctitle
import urllib3

from lib.service import Service


class TLSProxy(Service):

    myname = "tlsproxy"

    @classmethod
    def http_proxy_tunnel_connect(cls, proxyhost, proxyport, target):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxyhost = socket.gethostbyname(proxyhost)
        sock.settimeout(10)
        sock.connect((proxyhost, proxyport))
        cmd_connect = "CONNECT %s:%d HTTP/1.1\r\n\r\n" % target
        sock.sendall(cmd_connect.encode("utf-8"))
        response = []
        sock.settimeout(2)  # quick hack - replace this with something better performing.
        try:
            # in worst case this loop will take 2 seconds if not response was received (sock.timeout)
            while True:
                chunk = sock.recv(1024)
                if not chunk:  # if something goes wrong
                    break
                response.append(chunk.decode("utf-8"))
                if b"\r\n\r\n" in chunk:  # we do not want to read too far ;)
                    break
        except socket.error as se:
            if "timed out" not in se:
                response = [se]
        response = ''.join(response)
        if not "200 connection established" in response.lower():
            cls.log_error("Bad response from proxy to connect: %s" % repr(response))
            raise Exception("Unable to establish HTTP-Tunnel: %s" % repr(response))
        return sock

    @classmethod
    def copy_to_tls(cls, f, t):
        while not cls.eof and not cls.exit:
            try:
                data_in = f.recv(1024)
                if len(data_in) > 0:
                    t.send(data_in)
                else:
                    cls.eof = True
            except TimeoutError as e:
                pass
            except Exception as e:
                cls.eof = True
                cls.log_error("Socket error %s" % e)

    @classmethod
    def copy_from_tls(cls, f, t):
        while not cls.eof and not cls.exit:
            try:
                data_in = f.recv(1024)
                if len(data_in) > 0:
                    t.send(data_in)
                else:
                    cls.eof = True
            except TimeoutError as e:
                pass
            except Exception as e:
                cls.eof = True
                cls.log_error("Socket error %s" % e)

    @classmethod
    def accept_client(cls, conn, address):
        cls.log_debug("Connection from %s:%s to %s" % (address[0], address[1], cls.kwargs["port"]))
        s = cls.connect(cls.kwargs["gate"], cls.kwargs["gate"].get_ca())
        s.settimeout(0.01)
        conn.settimeout(0.01)
        cls.eof = False
        c1 = threading.Thread(target=cls.copy_from_tls, args=[conn, s])
        c2 = threading.Thread(target=cls.copy_to_tls, args=[s, conn])
        c1.start()
        c2.start()
        c1.join()
        c2.join()
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except Exception as e:
            pass
        try:
            s.shutdown(socket.SHUT_RDWR)
            s.close()
        except Exception as e:
            pass

    @classmethod
    def loop(cls):
        host = "127.0.0.1"
        port = cls.kwargs["port"]  # initiate port no above 1024s
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(10)
        server_socket.settimeout(1)
        cls.log_info("Running TLS proxy 127.0.0.1:%s -> %s" % (port, cls.kwargs["gate"].get_endpoint()))
        threads = []
        while not cls.exit:
            cls.log_debug("tlsserver 127.0.0.1:%s loop (%s connections)" % (port, len(threads)))
            while len(threads) > 20:
                cls.log_warning("Too many connections to 127.0.0.1:%s (%s)" % (port, len(threads)))
                time.sleep(5)
                continue
            tmp = copy(threads)
            for t in threads:
                if not t.is_alive():
                    t.join()
                    tmp.remove(t)
            threads = tmp

            try:
                conn, address = server_socket.accept()
                t = threading.Thread(target=cls.accept_client, args=[conn, address])
                t.start()
                threads.append(t)
            except TimeoutError:
                continue
        for t in threads:
            t.join()
        cls.log_warning("End of tlsproxy")

    @classmethod
    def connect(cls, gate, ca):
        try:
            if cls.ctrl["cfg"].use_http_proxy:
                proxydata = urllib3.util.parse_url(cls.ctrl["cfg"].use_http_proxy)
                s = cls.http_proxy_tunnel_connect(proxydata.host, proxydata.port, gate.get_endpoint(resolve=True))
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect(gate.get_endpoint(resolve=True))
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.load_verify_locations(cadata=ca)
            ctx.set_ciphers("HIGH")
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_REQUIRED
            client = ctx.wrap_socket(s)
            return client
        except Exception as e:
            cls.log_error("Cannot connect to %s: %s" % (gate.get_endpoint(), e))
            raise

    @classmethod
    def postinit(cls):
        cls.exit = False
        setproctitle.setproctitle("lvpn-tlsproxy 127.0.0.1:%s -> %s" % (cls.kwargs["port"], cls.kwargs["gate"].get_endpoint()))

    @classmethod
    def stop(cls):
        cls.exit = True
        cls.log_error("Exiting TLS proxy")
