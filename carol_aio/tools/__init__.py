"""Tool registry.

Tools are listed explicitly (not auto-discovered) so that PyInstaller can
see every import when building the exe. To add a tool: create a module in
this package with a ``Tool`` subclass and append the class to ``TOOLS``.
"""

from __future__ import annotations

from carol_aio.tool import Tool
from carol_aio.tools.edge_audio_pause import EdgeAudioPause

TOOLS: list[type[Tool]] = [EdgeAudioPause]


def create_tools() -> list[Tool]:
    return [cls() for cls in TOOLS]
