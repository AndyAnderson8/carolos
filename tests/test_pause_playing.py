"""The tool may only ever pause. These use fake media sessions that record every call."""

import asyncio
import sys
import unittest
from types import SimpleNamespace
from typing import Any
from unittest import mock

from carolos.tools import call_pause

PLAYING, PAUSED = 4, 5


class FakeSession:
    def __init__(self, app: str, status: int) -> None:
        self.source_app_user_model_id = app
        self.status = status
        self.calls: list[str] = []

    def get_playback_info(self) -> Any:
        return SimpleNamespace(playback_status=self.status)

    async def try_pause_async(self) -> bool:
        self.calls.append("pause")
        return True

    async def try_play_async(self) -> bool:
        self.calls.append("play")
        return True

    async def try_toggle_play_pause_async(self) -> bool:
        self.calls.append("toggle")
        return True


def pause(sessions: list[FakeSession], skip: str = "") -> list[str]:
    manager = SimpleNamespace(get_sessions=lambda: sessions)

    async def request_async() -> Any:
        return manager

    fake = SimpleNamespace(
        GlobalSystemMediaTransportControlsSessionManager=SimpleNamespace(
            request_async=request_async
        ),
        GlobalSystemMediaTransportControlsSessionPlaybackStatus=SimpleNamespace(
            PLAYING=PLAYING, PAUSED=PAUSED
        ),
    )
    with mock.patch.dict(sys.modules, {"winrt.windows.media.control": fake}):
        return asyncio.run(call_pause._pause_playing(skip))


class PausePlayingTest(unittest.TestCase):
    def test_only_playing_apps_are_paused_and_nothing_is_ever_started(self) -> None:
        spotify = FakeSession("Spotify.exe", PLAYING)
        chrome = FakeSession("Chrome", PAUSED)  # already paused: must be left exactly alone
        edge = FakeSession("MSEdge", PLAYING)  # the call: must be left alone
        paused = pause([spotify, chrome, edge], skip="msedge")
        self.assertEqual(paused, ["Spotify.exe"])
        self.assertEqual(spotify.calls, ["pause"])
        self.assertEqual(chrome.calls, [])
        self.assertEqual(edge.calls, [])

    def test_nothing_playing_means_no_calls_at_all(self) -> None:
        idle = [FakeSession("Spotify.exe", PAUSED), FakeSession("Chrome", PAUSED)]
        self.assertEqual(pause(idle), [])
        self.assertEqual([c for s in idle for c in s.calls], [])

    def test_the_only_call_ever_made_is_pause(self) -> None:
        sessions = [FakeSession("A", PLAYING), FakeSession("B", PAUSED), FakeSession("C", PLAYING)]
        pause(sessions)
        self.assertEqual({c for s in sessions for c in s.calls}, {"pause"})


if __name__ == "__main__":
    unittest.main()
