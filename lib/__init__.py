import os
import platform

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KCFG_KIVY_LOG_LEVEL"] = "debug"
os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
os.environ['KIVY_NO_CONSOLELOG'] = '1'  # eliminate console log
if platform.system() == "Windows":
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

