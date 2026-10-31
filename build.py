"""Build the app and its installer: python build.py

1. PyInstaller builds the app as a folder, dist/CarolAIO/.
2. Inno Setup wraps that into dist/CarolAIO-Setup-<version>.exe. If Inno Setup isn't
   installed this step is skipped with a warning (winget install JRSoftware.InnoSetup).

The version baked in is, in order: $CAROL_AIO_VERSION (set by CI), the git tag on the
current commit, the short commit hash, or "dev".
"""

import os
import shutil
import subprocess
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).parent
VERSION_FILE = ROOT / "carol_aio" / "_version.py"
ISS_FILE = ROOT / "installer" / "carol_aio.iss"


def git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def resolve_version() -> str:
    return (
        os.environ.get("CAROL_AIO_VERSION")
        or git("describe", "--tags", "--exact-match", "HEAD")
        or git("rev-parse", "--short", "HEAD")
        or "dev"
    )


def find_inno_compiler() -> str | None:
    found = os.environ.get("ISCC_PATH") or shutil.which("ISCC")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    for base in (
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.path.join(local, "Programs"),
    ):
        candidate = os.path.join(base, "Inno Setup 6", "ISCC.exe")
        if os.path.exists(candidate):
            return candidate
    return None


version = resolve_version()
VERSION_FILE.write_text(f'VERSION = "{version}"\n', encoding="utf-8")
print(f"Building Carol AIO {version}")

PyInstaller.__main__.run(
    [
        "main.py",
        "--name",
        "CarolAIO",
        "--windowed",
        "--noconfirm",
        "--icon",
        "assets/carol_aio.ico",
        "--add-data",
        "carol_aio/assets;carol_aio/assets",
        "--clean",
        "--collect-submodules",
        "comtypes",
        "--hidden-import",
        "pystray._win32",
        "--hidden-import",
        "carol_aio._version",
    ]
)

compiler = find_inno_compiler()
if compiler is None:
    print("WARNING: Inno Setup not found, so no installer was built (dist/CarolAIO/ is ready).")
else:
    subprocess.run([compiler, f"/DAppVersion={version}", str(ISS_FILE)], check=True)
    print(f"Installer: dist/CarolAIO-Setup-{version}.exe")
