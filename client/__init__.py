import os
import sys
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


    class SplashScreen(App):

        def build(self):
            my_splash_screen = Image(source=os.path.dirname(__file__) + '/../jukebox.png', pos=(800, 800))
            animation = Animation(x=0, y=0, d=2, t='out_bounce')
            animation.start(my_splash_screen)

            return my_splash_screen

    def splash_screen():
        SplashScreen().run()
