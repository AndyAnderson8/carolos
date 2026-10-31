"""Pause media when Microsoft Edge starts playing sustained audio (Windows).

Watches Edge's audio sessions through the Windows Core Audio peak meter. When
Edge goes from silent to audible, the tool samples the meter for a short
window; if the sound is sustained across that window it presses the global
Play/Pause media key, which pauses whatever is currently playing (Spotify,
YouTube, ...). It then waits for Edge to go quiet before re-arming, so it
never toggles playback back on.
"""

import ctypes
import sys
import time

from carol_aio.tool import Tool

PROCESS_NAME = "msedge.exe"
THRESHOLD = 0.02        # peak level (0..1) counted as "audible"
IDLE_POLL = 0.05        # seconds between checks while waiting for audio
BURST_WINDOW = 0.25     # seconds of repeated polling once audio is heard
BURST_POLL = 0.02       # seconds between samples inside the burst
SUSTAIN_RATIO = 0.8     # fraction of burst samples that must be audible

VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def is_sustained(read_peak, threshold=THRESHOLD, window=BURST_WINDOW, interval=BURST_POLL,
                 ratio=SUSTAIN_RATIO, sleep=time.sleep, clock=time.monotonic):
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


def press_play_pause():
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)


class EdgePeakReader:
    """Reads the loudest current peak across all Edge audio sessions."""

    def __init__(self):
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

        self._utils = AudioUtilities
        self._meter_iface = IAudioMeterInformation

    def __call__(self):
        peak = 0.0
        for session in self._utils.GetAllSessions():
            try:
                process = session.Process
                if process is None or process.name().lower() != PROCESS_NAME:
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

    def on_start(self):
        if sys.platform != "win32":
            raise RuntimeError("This tool only works on Windows.")
        self.run_in_thread(self._loop)

    def _loop(self, stop):
        import comtypes

        comtypes.CoInitialize()
        try:
            read_peak = EdgePeakReader()
            armed = True
            while not stop.is_set():
                audible = read_peak() >= THRESHOLD
                if not audible:
                    armed = True
                elif armed:
                    if is_sustained(read_peak):
                        press_play_pause()
                        armed = False  # wait for silence before re-arming
                stop.wait(IDLE_POLL)
        finally:
            comtypes.CoUninitialize()
