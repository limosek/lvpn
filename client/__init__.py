import os
import sys
import platform

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
