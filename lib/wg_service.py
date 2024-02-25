
from lib.service import Service, ServiceException


class WGService(Service):
    session = None
    myname = "wg_service"
