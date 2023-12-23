import sys
#from cx_Freeze import setup, Executable
import setuptools

# base="Win32GUI" should be used only for Windows GUI app
#base = "Win32GUI" if sys.platform == "win32" else None
base = None

msi_data = {
    "ProgId": [
        ("Lvpn.Client", None, None, "Lethean VPN Client", "IconId", None),
    ],
    "Shortcut": [
        ("DesktopShortcut",        # Shortcut
         "DesktopFolder",          # Directory_
         "LVPN",           # Name that will be show on the link
         "TARGETDIR",              # Component_
         "[TARGETDIR]client.exe",# Target exe to exexute
         None,                     # Arguments
         None,                     # Description
         None,                     # Hotkey
         None,                     # Icon
         None,                     # IconIndex
         None,                     # ShowCmd
         'TARGETDIR'               # WkDir
         )
    ]
}

bdist_msi_options = {
    "add_to_path": False,
    "data": msi_data
}

setuptools.setup(
    name="lvpn",
    version="0.3",
    author="Lukas Macura",
    author_email="lukas@macura.cz",
    description="Lvpn",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7'
)


"""
setup(
    executables=[
        Executable("client.py", base=base, shortcut_name="LVPN", shortcut_dir="DesktopFolder")
    ],
    options={
        "bdist_msi": bdist_msi_options
    }
)
"""

