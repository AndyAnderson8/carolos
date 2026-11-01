"""Only one copy of the app runs at a time (a named Windows mutex).

A second launch tells the running copy to open its panel (a named event) and exits.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable

MUTEX_NAME = "Local\\CaroLoS"
EVENT_NAME = "Local\CaroLoS-Show"
ERROR_ALREADY_EXISTS = 183
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0

_held = 0  # kept for the life of the process; Windows frees it on exit


def acquire(wait_seconds: float = 0) -> bool:
    """Take the lock; with ``wait_seconds`` it keeps trying for that long."""
    global _held
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    deadline = time.monotonic() + wait_seconds
    while True:
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if handle and ctypes.get_last_error() != ERROR_ALREADY_EXISTS:
            _held = handle
            return True
        if handle:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def _kernel32() -> ctypes.WinDLL:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.SetEvent.argtypes = [ctypes.c_void_p]
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    return kernel32


def signal_running() -> None:
    """Ask the copy that is already running to show its panel."""
    if sys.platform != "win32":
        return
    kernel32 = _kernel32()
    handle = kernel32.CreateEventW(None, False, False, EVENT_NAME)
    if handle:
        kernel32.SetEvent(handle)
        kernel32.CloseHandle(handle)


def listen(on_signal: Callable[[], None]) -> None:
    """Call ``on_signal`` (from a background thread) whenever a second copy is launched."""
    if sys.platform != "win32":
        return
    kernel32 = _kernel32()
    handle = kernel32.CreateEventW(None, False, False, EVENT_NAME)
    if not handle:
        return

    def wait() -> None:
        while kernel32.WaitForSingleObject(handle, INFINITE) == WAIT_OBJECT_0:
            on_signal()

    threading.Thread(target=wait, daemon=True).start()
