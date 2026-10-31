"""Base class every mini-tool derives from."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    """One configurable setting; drives both validation and the settings dialog."""

    key: str
    label: str
    type: type  # float, int, str or bool
    default: Any
    min: float | None = None
    max: float | None = None
    help: str = ""

    def coerce(self, value: Any) -> Any:
        """Return ``value`` as this field's type or raise ValueError."""
        if self.type is bool:
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in ("true", "yes", "on", "1"):
                return True
            if text in ("false", "no", "off", "0"):
                return False
            raise ValueError(f"{value!r} is not true/false")
        if self.type is str:
            text = str(value).strip()
            if not text:
                raise ValueError("must not be empty")
            return text
        if isinstance(value, bool):
            raise ValueError(f"{value!r} is not a number")
        try:
            number = self.type(value)
        except (TypeError, ValueError):
            raise ValueError(f"{value!r} is not a valid {self.type.__name__}") from None
        if (self.min is not None and number < self.min) or (
            self.max is not None and number > self.max
        ):
            raise ValueError(f"must be between {self.min} and {self.max}")
        return number


class Tool:
    """A mini-tool the AIO app can switch on and off.

    Subclasses set ``key``, ``name`` and ``description`` and implement
    ``on_start`` / ``on_stop``. ``on_start`` must return quickly; spawn a
    thread via ``self.run_in_thread`` for long-running work.
    """

    key = ""
    name = ""
    description = ""
    fields: tuple[Field, ...] = ()  # empty means the tool has no settings

    def __init__(self) -> None:
        self.settings: dict[str, Any] = self.defaults()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        try:
            self.on_start()
        except Exception:
            self._running = False
            raise

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        try:
            self.on_stop()
        finally:
            if self._thread is not None and self._thread is not threading.current_thread():
                self._thread.join(timeout=2)
            self._thread = None

    def defaults(self) -> dict[str, Any]:
        return {f.key: f.default for f in self.fields}

    def configure(self, raw: Any) -> list[str]:
        """Validate ``raw`` against ``fields`` and swap in the result.

        Invalid or missing values fall back to defaults. Returns a list of
        error strings. The settings dict is replaced wholesale, so worker
        threads can safely read ``self.settings`` at any time.
        """
        raw = raw if isinstance(raw, dict) else {}
        settings = self.defaults()
        errors: list[str] = []
        for f in self.fields:
            if f.key in raw:
                try:
                    settings[f.key] = f.coerce(raw[f.key])
                except ValueError as exc:
                    errors.append(f"{self.key}.{f.key}: {exc}")
        self.settings = settings
        return errors

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start()
        else:
            self.stop()

    def run_in_thread(self, target: Callable[[threading.Event], None]) -> None:
        """Run ``target(stop_event)`` on a daemon thread until the tool stops."""
        self._thread = threading.Thread(
            target=target, args=(self._stop_event,), name=self.key or self.name, daemon=True
        )
        self._thread.start()

    def on_start(self) -> None:
        raise NotImplementedError

    def on_stop(self) -> None:
        pass
