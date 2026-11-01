"""Only one copy of the app runs at a time (a named Windows mutex)."""

from __future__ import annotations

import ctypes
import sys
import time

MUTEX_NAME = "Local\\CaroLoS"
ERROR_ALREADY_EXISTS = 183

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
