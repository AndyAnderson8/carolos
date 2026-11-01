"""Tool registry.

Tools are listed explicitly (not auto-discovered) so that PyInstaller can
see every import when building the exe. To add a tool: create a module in
this package with a ``Tool`` subclass and append the class to ``TOOLS``.
"""

from __future__ import annotations

from carolos.tool import Tool
from carolos.tools.call_pause import CallPause

TOOLS: list[type[Tool]] = [CallPause]


def create_tools() -> list[Tool]:
    return [cls() for cls in TOOLS]
