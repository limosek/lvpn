import datetime

from lib.registry import Registry
from lib.vdpobject import VDPObject, VDPException


class Space(VDPObject):

    tpe = 'Space'

    def __init__(self, spaceinfo, file=None, vdp=None):
        if not vdp:
            vdp = Registry.vdp
        self.validate(spaceinfo, "Space", file)
        self._data = spaceinfo
        self._provider = vdp.get_provider(self._data["providerid"])
        if not self._provider:
            raise VDPException("Unknown providerid %s" % self._data["providerid"])
        self._local = self._provider.is_local()
        self._file = file

    def get_id(self):
        return self.get_provider_id() + "." + self._data["spaceid"]

    def get_wallet(self):
        return self.get_provider().get_wallet()

    def set_provider(self, provider):
        self._provider = provider
        self._local = self._provider.is_local()

    def get_title(self):
        return "%s, provider=%s, revision=%s, ttl=%s, expiry=%s" % (
            self._data["name"],
            self.get_provider().get_name(),
            self.get_revision(),
            self.get_ttl(),
            datetime.datetime.fromtimestamp(self.get_expiry())
        )

    def activate_client(self, session):
        pass

    def activate_server(self, session):
        return True

    def deactivate_client(self, session):
        pass

    def deactivate_server(self, session):
        return True

    def __repr__(self):
        if Registry.cfg.is_server:
            return "Space %s/%s[local=%s]" % (self._data["spaceid"], self._data["name"], self.is_local())
        else:
            return "Space %s/%s" % (self._data["spaceid"], self._data["name"])
