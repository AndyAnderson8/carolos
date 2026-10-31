"""Build the single-file Windows exe: python build.py"""

import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "main.py",
        "--name", "CarolAIO",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--collect-submodules", "comtypes",
    ]
)
