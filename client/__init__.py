import os
os.environ["KIVY_NO_ARGS"] = "1"
os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
os.environ['KIVY_NO_CONSOLELOG'] = '1'  # eliminate console log

from client.gui_switcher import Switcher
from client.gui_status import Status
from client.gui_wizard import Wizard
from client.gui import GUI
