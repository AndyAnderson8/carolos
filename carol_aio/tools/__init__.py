"""Tool registry.

Tools are listed explicitly (not auto-discovered) so that PyInstaller can
see every import when building the exe. To add a tool: create a module in
this package with a ``Tool`` subclass and append the class to ``TOOLS``.
"""

TOOLS = []


def create_tools():
    return [cls() for cls in TOOLS]
