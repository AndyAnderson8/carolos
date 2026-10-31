"""YAML config shared by the GUI and hand edits.

Layout::

    tools:
      <tool key>:
        enabled: false
        settings:
          <field>: <value>

The file lives next to the exe (or in the repo root when run from source).
The GUI writes to it on every change and reloads it when it is edited by hand.
"""

import os
import sys
from pathlib import Path

import yaml

HEADER = (
    "# Carol AIO config. Edit here or via the gear buttons in the app;\n"
    "# changes made in this file are picked up while the app is running.\n"
)


class ConfigError(Exception):
    pass


ENV_VAR = "CAROL_AIO_CONFIG"


_override = None


def set_config_path(path):
    global _override
    _override = path


def default_config_path():
    """``--config`` (via ``set_config_path``) > $CAROL_AIO_CONFIG > next to the exe."""
    override = _override or os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "config.yaml"


class Config:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_config_path()
        self.data = {"tools": {}}
        self._mtime = None

    def _disk_mtime(self):
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def changed_on_disk(self):
        return self._disk_mtime() != self._mtime

    def load(self):
        """Read the file. Raises ConfigError (keeping old data) if it is invalid."""
        self._mtime = self._disk_mtime()
        if self._mtime is None:
            return
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
            raise ConfigError(f"Could not read {self.path.name}: {exc}") from exc
        if raw is None:
            raw = {}
        if not isinstance(raw, dict) or not isinstance(raw.get("tools", {}), (dict, type(None))):
            raise ConfigError(f"{self.path.name}: expected a 'tools:' mapping at the top level")
        self.data = {**raw, "tools": raw.get("tools") or {}}

    def tool_section(self, key):
        section = self.data["tools"].get(key)
        if not isinstance(section, dict):
            section = {}
        settings = section.get("settings")
        return {
            "enabled": section.get("enabled") is True,
            "settings": settings if isinstance(settings, dict) else {},
        }

    def set_tool(self, key, enabled=None, settings=None):
        section = self.tool_section(key)
        if enabled is not None:
            section["enabled"] = bool(enabled)
        if settings is not None:
            section["settings"] = dict(settings)
        self.data["tools"][key] = section

    def save(self):
        text = HEADER + yaml.safe_dump(self.data, sort_keys=False, default_flow_style=False)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.path)
        self._mtime = self._disk_mtime()
