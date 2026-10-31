"""Base class every mini-tool derives from."""

import threading


class Tool:
    """A mini-tool the AIO app can switch on and off.

    Subclasses set ``key``, ``name`` and ``description`` and implement
    ``on_start`` / ``on_stop``. ``on_start`` must return quickly; spawn a
    thread via ``self.run_in_thread`` for long-running work.
    """

    key = ""
    name = ""
    description = ""

    def __init__(self):
        self._running = False
        self._stop_event = threading.Event()
        self._thread = None

    @property
    def running(self):
        return self._running

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        try:
            self.on_start()
        except Exception:
            self._running = False
            raise

    def stop(self):
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

    def set_enabled(self, enabled):
        self.start() if enabled else self.stop()

    def run_in_thread(self, target):
        """Run ``target(stop_event)`` on a daemon thread until the tool stops."""
        self._thread = threading.Thread(
            target=target, args=(self._stop_event,), name=self.key or self.name, daemon=True
        )
        self._thread.start()

    def on_start(self):
        raise NotImplementedError

    def on_stop(self):
        pass
