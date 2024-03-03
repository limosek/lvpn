import os

if "NO_KIVY" not in os.environ:
    try:
        import kivy
    except ModuleNotFoundError:
        os.environ["NO_KIVY"] = "1"

from server.arguments import ServerArguments
from server.http import Manager
from server.stripe import StripeManager
from server.wallet import ServerWallet
from server.wg_service import WGServerService

