import os
import platform

if "NO_KIVY" not in os.environ:
    try:
        import kivy
    except ModuleNotFoundError:
        os.environ["NO_KIVY"] = "1"

if "NO_KIVY" not in os.environ:
    if platform.system() == "Windows":
        os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

    from client.gui_switcher import Switcher
    from client.gui_status import Status
    from client.gui_wizard import Wizard
    from client.gui import GUI
    from kivy_garden.qrcode import QRCodeWidget
    from kivy.app import App
    from kivy.uix.image import Image
    from kivy.animation import Animation

from client.arguments import ClientArguments
from client.proxy import Proxy
