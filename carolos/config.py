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

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

HEADER = (
    "# CaroLoS config. Edit here or via the gear buttons in the app;\n"
    "# changes made in this file are picked up while the app is running.\n"
)


class ConfigError(Exception):
    pass


ENV_VAR = "CAROLOS_CONFIG"

# Tools that were renamed: old key -> new key. Saved settings move over on load.
RENAMED_TOOLS = {"edge_audio_pause": "call_pause"}


_override: str | None = None


def set_config_path(path: str | None) -> None:
    global _override
    _override = path


def default_config_path() -> Path:
    """``--config`` (via ``set_config_path``) > $CAROLOS_CONFIG > next to the exe."""
    override = _override or os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "config.yaml"


class Config:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_config_path()
        self.data: dict[str, Any] = {"tools": {}}
        self._signature: tuple[int, int] | None = None

    def _disk_signature(self) -> tuple[int, int] | None:
        """Modified time plus size, so same-tick edits that change length are seen."""
        try:
            stat = self.path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def changed_on_disk(self) -> bool:
        return self._disk_signature() != self._signature

    def load(self) -> None:
        """Read the file. Raises ConfigError (keeping old data) if it is invalid."""
        self._signature = self._disk_signature()
        if self._signature is None:
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
        for old, new in RENAMED_TOOLS.items():
            if old in self.data["tools"] and new not in self.data["tools"]:
                self.data["tools"][new] = self.data["tools"].pop(old)

    def tool_section(self, key: str) -> dict[str, Any]:
        section = self.data["tools"].get(key)
        if not isinstance(section, dict):
            section = {}
        settings = section.get("settings")
        return {
            "enabled": section.get("enabled") is True,
            "settings": settings if isinstance(settings, dict) else {},
        }

    def set_tool(
        self,
        key: str,
        enabled: bool | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        section = self.tool_section(key)
        if enabled is not None:
            section["enabled"] = bool(enabled)
        if settings is not None:
            section["settings"] = dict(settings)
        self.data["tools"][key] = section

    def save(self) -> None:
        text = HEADER + yaml.safe_dump(self.data, sort_keys=False, default_flow_style=False)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.path)
        self._signature = self._disk_signature()
