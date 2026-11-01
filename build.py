"""Build the app and its installer: python build.py [--deploy]

1. PyInstaller builds the app as a folder, dist/CaroLoS/.
2. Inno Setup wraps that into dist/CaroLoS-Setup-<version>.exe. If Inno Setup isn't
   installed this step is skipped with a warning (winget install JRSoftware.InnoSetup).

--deploy is for testing without reinstalling: it builds just the folder (incrementally),
stops the running app, copies the new files over the installed copy, keeping its
config.yaml and uninstaller, and starts it again.

The version baked in is, in order: $CAROLOS_VERSION (set by CI), the git tag on the
current commit, the short commit hash, or "dev". A --deploy build adds "-dev".
"""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).parent
DIST_APP = ROOT / "dist" / "CaroLoS"
VERSION_FILE = ROOT / "carolos" / "_version.py"
ISS_FILE = ROOT / "installer" / "carolos.iss"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{1E326CCF-AD36-4976-B6BC-4746BF507E81}_is1"
DETACHED = 0x00000008  # DETACHED_PROCESS


def git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def resolve_version() -> str:
    return (
        os.environ.get("CAROLOS_VERSION")
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


def installed_folder() -> Path | None:
    """Where the installer put the app, from its Settings > Apps entry."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            return Path(str(winreg.QueryValueEx(key, "InstallLocation")[0]))
    except OSError:
        return None


def deploy() -> None:
    """Swap the freshly built files into the installed app and start it again."""
    folder = installed_folder()
    if folder is None or not folder.exists():
        raise SystemExit("CaroLoS isn't installed, so there is nothing to update. Run the setup.")
    for name in ("CaroLoS.exe", "CarolAIO.exe"):  # the second is the app's old name
        subprocess.run(["taskkill", "/IM", name, "/F", "/T"], capture_output=True)
    for attempt in range(10):  # Windows can hold the old exe for a moment after it exits
        time.sleep(1)
        try:
            shutil.rmtree(
                folder / "_internal", ignore_errors=True
            )  # no leftovers from older builds
            shutil.copytree(
                DIST_APP,
                folder,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("config.yaml", "unins*"),
            )
            break
        except (shutil.Error, OSError):
            if attempt == 9:
                raise
    (folder / "CarolAIO.exe").unlink(missing_ok=True)
    subprocess.Popen([str(folder / "CaroLoS.exe")], cwd=folder, creationflags=DETACHED)
    print(f"Deployed to {folder} and restarted it.")


parser = argparse.ArgumentParser(description="Build CaroLoS")
parser.add_argument(
    "--deploy", action="store_true", help="update the installed copy in place, no installer"
)
args = parser.parse_args()

version = resolve_version()
if args.deploy and "CAROLOS_VERSION" not in os.environ:
    version += "-dev"
VERSION_FILE.write_text(f'VERSION = "{version}"\n', encoding="utf-8")
print(f"Building CaroLoS {version}")

PyInstaller.__main__.run(
    [
        "main.py",
        "--name",
        "CaroLoS",
        "--windowed",
        "--noconfirm",
        "--icon",
        "assets/carolos.ico",
        "--add-data",
        "carolos/assets;carolos/assets",
        "--collect-submodules",
        "comtypes",
        "--hidden-import",
        "pystray._win32",
        "--hidden-import",
        "carolos._version",
    ]
    + ([] if args.deploy else ["--clean"])  # an incremental build is much faster
)

if args.deploy:
    deploy()
else:
    compiler = find_inno_compiler()
    if compiler is None:
        print("WARNING: Inno Setup not found, so no installer was built (dist/CaroLoS/ is ready).")
    else:
        subprocess.run([compiler, f"/DAppVersion={version}", str(ISS_FILE)], check=True)
        print(f"Installer: dist/CaroLoS-Setup-{version}.exe")
