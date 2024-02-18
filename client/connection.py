import logging
import secrets
import socket
from copy import copy

from lib.sessions import Sessions


class Connection:

    def __init__(self, cfg, session=None, data=None, parent=None, connection=None, port=None):
        if connection:
            self._data = connection
            sessions = Sessions(cfg, noload=True)
            session = sessions.get(connection["sessionid"])
            if not session:
                raise Exception("Non-existent session %s for connection %s" % (connection["sessionid"], connection["connectionid"]))
        elif session:
            self._data = {
                "connectionid": "c-" + secrets.token_hex(8),
                "sessionid": session.get_id(),
                "children": [],
                "data": {}
            }
            if parent:
                self._data["parent"] = parent
            if port:
                self._data["port"] = port
        else:
            raise Exception("Need sessionid or data")
        if data:
            self._data["data"] = data
        self._session = session
        self._gate = cfg.vdp.get_gate(self._session.get_gateid())
        self._space = cfg.vdp.get_space(self._session.get_spaceid())

    def get_id(self):
        return self._data["connectionid"]

    def get_sessionid(self):
        return self._data["sessionid"]

    def get_session(self):
        return self._session

    def get_dict(self):
        return self._data

    def get_port(self):
        if "port" in self._data:
            return self._data["port"]
        else:
            return None

    def get_space(self):
        return self._space

    def get_gate(self):
        return self._gate

    def get_parent(self):
        return self._data["parent"]

    def add_children(self, connectionid):
        self._data["children"].append(connectionid)

    def get_children(self):
        return self._data["children"]

    def get_data(self):
        return self._data["data"]

    def set_data(self, data):
        self._data["data"] = data

    def get_title(self):
        txt = "%s/%s[id=%s,port=%s]" % (self.get_gate().get_title(), self.get_space().get_title(), self.get_id(), self.get_port())
        return txt

    def check_alive(self):
        if self.get_port():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            try:
                s.connect(("127.0.0.1", self.get_port()))
                s.close()
                logging.getLogger().info("Connection %s is alive" % self.get_id())
                return True
            except Exception as e:
                logging.getLogger().error("Connection %s is dead: %s" % (self.get_id(), e))
                return False
        return True

    def __repr__(self):
        if "port" in self._data:
            txt = "Connection/%s[port=%s][%s/%s/%s]" % (
                self.get_id(), self._data["port"], self.get_gate().get_title(), self.get_space().get_title(), self.get_sessionid())
        else:
            txt = "Connection/%s[%s/%s/%s]" % (
                self.get_id(), self.get_gate().get_title(), self.get_space().get_title(), self.get_sessionid())
        return txt


class Connections:

    def __init__(self, connections=None):
        if connections is None:
            connections = []
        self._data = connections

    def get(self, id):
        for c in self._data:
            if c.get_id() == id:
                return c
        return False

    def is_connected(self, gateid, spaceid):
        for c in self._data:
            if c.get_gate().get_id() == gateid and c.get_space().get_id() == spaceid:
                return True
        return False

    def get_by_sessionid(self, sessionid):
        for c in self._data:
            if c.get_sessionid() == sessionid:
                return c
        return False

    def add(self, connection):
        self._data.append(connection)

    def remove(self, connectionid):
        removed = False
        for c in copy(self._data):
            if c.get_id() == connectionid:
                self._data.remove(c)
                removed = True
        if not removed:
            logging.getLogger().error("Removing non-existent connection %s" % connectionid)

    def find_replaced(self, connection):
        for c in self._data:
            if c.get_gate().get_id() == connection.get_gate().get_id():
                return c

    def get_dict(self):
        return self._data

    def check_alive(self):
        for c in self._data:
            if not c.check_alive():
                self.remove(c.get_id())

    def __repr__(self):
        return "%s active connections" % len(self._data)

