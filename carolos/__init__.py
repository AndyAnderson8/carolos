"""CaroLoS: a small all-in-one host for tools."""

from importlib import import_module


def _version() -> str:
    """The release tag or commit baked in by build.py; "dev" when run from source."""
    try:
        return str(import_module("carolos._version").VERSION)
    except ImportError:
        return "dev"


__version__ = _version()
