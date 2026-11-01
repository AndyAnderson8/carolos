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


def friendly_name(app: str) -> str:
    """ "msedge.exe" or "MSEdge" -> "Microsoft Edge"; other programs get a tidied-up name."""
    key = app.lower()
    known = KNOWN.get(key) or KNOWN.get(key + ".exe")
    if known:
        return known
    name = app.rsplit("!", 1)[-1]  # Store apps: "Publisher.App_id!Publisher.App"
    name = name[:-4] if name.lower().endswith(".exe") else name.rsplit(".", 1)[-1]
    name = name.replace("_", " ").replace("-", " ")
    return name if any(c.isupper() for c in name) else name.title()


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
