"""Build the single-file Windows exe: python build.py"""

import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "main.py",
        "--name",
        "CarolAIO",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--icon",
        "assets/carol_aio.ico",
        "--add-data",
        "carol_aio/assets/pianta_face.png;carol_aio/assets",
        "--clean",
        "--collect-submodules",
        "comtypes",
        "--hidden-import",
        "pystray._win32",
    ]
)
