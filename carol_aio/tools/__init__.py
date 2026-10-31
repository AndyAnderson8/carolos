"""Tool registry.

Tools are listed explicitly (not auto-discovered) so that PyInstaller can
see every import when building the exe. To add a tool: create a module in
this package with a ``Tool`` subclass and append the class to ``TOOLS``.
"""

from carol_aio.tools.edge_audio_pause import EdgeAudioPause

TOOLS = [EdgeAudioPause]


def create_tools():
    return [cls() for cls in TOOLS]
