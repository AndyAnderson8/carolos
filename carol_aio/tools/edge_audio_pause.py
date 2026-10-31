"""Pause media when Microsoft Edge starts playing sustained audio (Windows).

Watches Edge's audio sessions through the Windows Core Audio peak meter. When
Edge goes from silent to audible, the tool samples the meter for a short
window; if the sound is sustained across that window it presses the global
Play/Pause media key, which pauses whatever is currently playing (Spotify,
YouTube, ...). It then waits for Edge to go quiet before re-arming, so it
never toggles playback back on.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

from carol_aio.tool import Field, Tool

PROCESS_NAME = "msedge.exe"
THRESHOLD = 0.02
IDLE_POLL = 0.05  # seconds between checks while waiting for audio
BURST_WINDOW = 0.25
BURST_POLL = 0.02
SUSTAIN_RATIO = 0.8

VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def is_sustained(
    read_peak: Callable[[], float],
    threshold: float = THRESHOLD,
    window: float = BURST_WINDOW,
    interval: float = BURST_POLL,
    ratio: float = SUSTAIN_RATIO,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Poll ``read_peak`` for ``window`` seconds; True if mostly above ``threshold``."""
    loud = total = 0
    end = clock() + window
    while True:
        total += 1
        if read_peak() >= threshold:
            loud += 1
        if clock() >= end:
            break
        sleep(interval)
    return loud / total >= ratio


def press_play_pause() -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)


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


class EdgeAudioPause(Tool):
    key = "edge_audio_pause"
    name = "Edge Audio Pauser"
    description = "Pauses Spotify/YouTube/etc. when Edge starts playing sustained audio."
    fields = (
        Field(
            "process_name",
            "Process to watch",
            str,
            PROCESS_NAME,
            help="Executable whose audio is monitored.",
        ),
        Field(
            "threshold",
            "Volume threshold",
            float,
            THRESHOLD,
            0.0,
            1.0,
            "Peak level (0-1) counted as audible.",
        ),
        Field(
            "burst_window",
            "Sustain window (s)",
            float,
            BURST_WINDOW,
            0.05,
            5.0,
            "How long to poll after audio starts.",
        ),
        Field(
            "burst_poll",
            "Poll interval (s)",
            float,
            BURST_POLL,
            0.005,
            1.0,
            "Delay between samples inside the window.",
        ),
        Field(
            "sustain_ratio",
            "Sustain ratio",
            float,
            SUSTAIN_RATIO,
            0.0,
            1.0,
            "Fraction of samples that must be audible to pause.",
        ),
    )

    def on_start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("This tool only works on Windows.")
        self.run_in_thread(self._loop)

    def _loop(self, stop: threading.Event) -> None:
        import comtypes

        comtypes.CoInitialize()
        try:
            read_peak = EdgePeakReader()
            armed = True
            while not stop.is_set():
                cfg = self.settings
                read_peak.process_name = cfg["process_name"].lower()
                audible = read_peak() >= cfg["threshold"]
                if not audible:
                    armed = True
                elif armed:
                    if is_sustained(
                        read_peak,
                        cfg["threshold"],
                        cfg["burst_window"],
                        cfg["burst_poll"],
                        cfg["sustain_ratio"],
                    ):
                        press_play_pause()
                        armed = False  # wait for silence before re-arming
                stop.wait(IDLE_POLL)
        finally:
            comtypes.CoUninitialize()
