"""How the app was installed. The Inno Setup installer does the installing; see installer/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

UNINSTALLER = "unins000.exe"  # Inno Setup puts this next to the app
DETACHED = 0x00000008  # DETACHED_PROCESS


def running_exe() -> Path | None:
    """The exe this process came from, or None when run from source."""
    return Path(sys.executable).resolve() if getattr(sys, "frozen", False) else None


def is_installed() -> bool:
    """True when running from a folder the installer set up (it leaves an uninstaller beside us)."""
    exe = running_exe()
    return exe is not None and (exe.parent / UNINSTALLER).exists()


def run_setup(setup: Path) -> None:
    """Start a downloaded installer silently. It stops the app, replaces it and relaunches it."""
    subprocess.Popen(
        [str(setup), "/SILENT", "/NORESTART"],
        creationflags=DETACHED,
        close_fds=True,
    )
