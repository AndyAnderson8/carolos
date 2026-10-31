"""Which programs can make sound right now, with names a person would recognise."""

from __future__ import annotations

import sys

KNOWN = {
    "msedge.exe": "Microsoft Edge",
    "chrome.exe": "Google Chrome",
    "firefox.exe": "Firefox",
    "brave.exe": "Brave",
    "opera.exe": "Opera",
    "vivaldi.exe": "Vivaldi",
    "spotify.exe": "Spotify",
    "vlc.exe": "VLC",
    "discord.exe": "Discord",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "zoom.exe": "Zoom",
    "slack.exe": "Slack",
}


def friendly_name(exe: str) -> str:
    """ "msedge.exe" -> "Microsoft Edge"; unknown programs get a tidied-up file name."""
    known = KNOWN.get(exe.lower())
    if known:
        return known
    stem = exe[:-4] if exe.lower().endswith(".exe") else exe
    return stem.replace("_", " ").replace("-", " ").title()


def running_audio_apps() -> list[str]:
    """Executable names of programs that currently have an audio session (Windows only)."""
    if sys.platform != "win32":
        return []
    try:
        from pycaw.pycaw import AudioUtilities

        names = set()
        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            if process is not None:
                names.add(process.name().lower())
        return sorted(names)
    except Exception:
        return []
