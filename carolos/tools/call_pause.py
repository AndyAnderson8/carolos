"""Pause media the moment a call announces itself with sound in Microsoft Edge (Windows).

Watches Edge's audio sessions through the Windows Core Audio peak meter. As soon as
Edge makes any sound it asks Windows' media session manager to pause every app that
is currently playing (Spotify, YouTube in another browser, ...). Only sessions that
are playing are paused, so nothing is ever started by mistake, and Edge's own session
is skipped so a call is left alone. It then waits for Edge to go quiet before it can
pause again.
"""

from __future__ import annotations

import asyncio
import sys
import threading
from typing import Any

from carolos.audio_apps import friendly_name, running_audio_apps
from carolos.tool import Field, Tool

PROCESS_NAME = "msedge.exe"
THRESHOLD = 0.001  # Edge reads exactly 0 when silent, so any signal counts
IDLE_POLL = 0.05  # seconds between checks while waiting for audio


class SoundTrigger:
    """Fires once when sound starts, then not again until it has gone quiet."""

    def __init__(self) -> None:
        self.armed = True

    def update(self, audible: bool) -> bool:
        """Feed the latest reading; True means "sound just started: pause now"."""
        if not audible:
            self.armed = True
            return False
        fire, self.armed = self.armed, False
        return fire


async def _pause_playing(skip: str) -> list[str]:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as Manager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
    )

    manager = await Manager.request_async()
    paused: list[str] = []
    for session in manager.get_sessions():
        app = session.source_app_user_model_id
        if skip and skip in app.lower():
            continue
        if session.get_playback_info().playback_status != Status.PLAYING:
            continue
        if await session.try_pause_async():
            paused.append(app)
    return paused


def pause_playing_media(skip: str = "") -> list[str]:
    """Pause every playing media session whose app id doesn't contain ``skip``.

    Pausing is all this ever does: it never plays, resumes or toggles anything.

    Returns the app ids that were paused. Runs on its own thread because the
    WinRT calls need a different COM apartment than the audio meter's thread.
    """
    result: list[str] = []
    worker = threading.Thread(
        target=lambda: result.extend(asyncio.run(_pause_playing(skip.lower()))),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=5)
    return result


class EdgePeakReader:
    """Reads the loudest current peak across all Edge audio sessions."""

    def __init__(self) -> None:
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

        self.process_name = PROCESS_NAME
        self._utils = AudioUtilities
        self._meter_iface = IAudioMeterInformation

    def __call__(self) -> float:
        peak = 0.0
        for session in self._utils.GetAllSessions():
            try:
                process = session.Process
                if process is None or process.name().lower() != self.process_name:
                    continue
                meter = session._ctl.QueryInterface(self._meter_iface)
                peak = max(peak, meter.GetPeakValue())
            except Exception:
                continue  # session ended between enumeration and query
        return peak


class CallPause(Tool):
    key = "call_pause"
    name = "Pause media for calls"
    description = "Stops Spotify, YouTube and anything else playing when a call starts."
    fields = (
        Field(
            "process_name",
            "App that plays the call sound",
            str,
            PROCESS_NAME,
            picker=True,
            help="The app that says the brand name before a call. Apps show up here once they have made sound.",
        ),
    )

    def options(self, key: str) -> list[tuple[str, str]]:
        if key != "process_name":
            return []
        apps = {PROCESS_NAME, self.settings["process_name"].lower(), *running_audio_apps()}
        return sorted(((exe, friendly_name(exe)) for exe in apps), key=lambda o: o[1].lower())

    def on_start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("This tool only works on Windows.")
        self.run_in_thread(self._loop)

    def _loop(self, stop: threading.Event) -> None:
        import comtypes

        comtypes.CoInitialize()
        try:
            read_peak = EdgePeakReader()
            trigger = SoundTrigger()
            while not stop.is_set():
                cfg = self.settings
                read_peak.process_name = cfg["process_name"].lower()
                if trigger.update(read_peak() >= THRESHOLD):
                    pause_playing_media(cfg["process_name"].lower().removesuffix(".exe"))
                stop.wait(IDLE_POLL)
        finally:
            comtypes.CoUninitialize()
