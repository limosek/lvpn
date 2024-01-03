import os
import sys
import platform

if not "NO_KIVY" in os.environ:
    os.environ["KIVY_NO_ARGS"] = "1"
    os.environ["KCFG_KIVY_LOG_LEVEL"] = "debug"
    #os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
    if getattr(sys, 'frozen', False):
        os.environ['KIVY_NO_CONSOLELOG'] = '1'  # eliminate console log
    if platform.system() == "Windows":
        os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

    from client.gui_switcher import Switcher
    from client.gui_status import Status
    from client.gui_wizard import Wizard
    from client.gui import GUI
