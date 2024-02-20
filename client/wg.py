import logging
import multiprocessing
import os
import time

from client.connection import Connection, Connections
from lib.mngrrpc import ManagerRpcCall, ManagerException
from lib.runcmd import RunCmd
from lib.service import Service, ServiceException
from lib.session import Session
from lib.sessions import Sessions
from lib.messages import Messages
from lib.util import Util


class WGService(Service):

    myname = "wg"

    @classmethod
    def postinit(cls):
        cls.exit = False

    @classmethod
    def prepare(cls, session, wg_dev):
        wgdata = session.get_gate_data("wg")
        if wgdata:
            pass
