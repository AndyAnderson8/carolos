"""The update dialogs, and what each button does."""

from __future__ import annotations

import tempfile
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from carol_aio import __version__, install, updates
from carol_aio.dialogs import Choice, Prompt

Post = Callable[[Callable[[], None]], None]  # run something on the Tk thread


class Updater:
    """Checks GitHub for a newer release and walks through downloading its installer.

    Once the installer is downloaded it hands the file to ``on_update``; the app
    then quits and runs it, and the installer replaces the app and relaunches it.
    """

    def __init__(self, root: tk.Tk, post: Post, on_update: Callable[[Path], None]) -> None:
        self.root, self.post, self.on_update = root, post, on_update
        self._busy = False
        self._prompt: Prompt | None = None

    def check(self, manual: bool) -> None:
        """Look for an update. Automatic checks stay quiet unless there is one to offer."""
        if not install.is_installed():
            if manual:
                self._tell(
                    "Updates",
                    "Updates apply to the installed app. Install Carol AIO with its setup "
                    "program to get them.",
                )
            return
        if self._busy or self._open():
            self._raise()
            return
        self._busy = True
        threading.Thread(target=self._look, args=(manual,), daemon=True).start()

    def _look(self, manual: bool) -> None:
        try:
            result, error = updates.check(__version__), ""
        except updates.UpdateError as exc:
            result, error = None, str(exc)
        self.post(lambda: self._looked(result, error, manual))

    def _looked(self, result: updates.CheckResult | None, error: str, manual: bool) -> None:
        self._busy = False
        if result is not None and result.update is not None:
            self._offer(result.update)
        elif manual:
            if error:
                self._tell("Couldn't check for updates", error)
            elif result is None or result.latest is None:
                self._tell("Updates", "No releases have been published yet.")
            else:
                self._tell("You're up to date", f"Carol AIO {__version__} is the latest version.")

    def _open(self) -> bool:
        return self._prompt is not None and bool(self._prompt.winfo_exists())

    def _raise(self) -> None:
        if self._prompt is not None and self._prompt.winfo_exists():
            self._prompt.lift()

    def _tell(self, title: str, message: str) -> None:
        self._prompt = Prompt(self.root, title, message, [Choice("OK", primary=True)])

    def _offer(self, release: updates.Release) -> None:
        prompt = Prompt(
            self.root,
            "Update available",
            f"Carol AIO {release.version} is ready. You have {__version__}.",
            [],
            detail=release.notes,
        )
        prompt.set_choices(
            [
                Choice("Later"),
                Choice("Update now", lambda: self._download(prompt, release), True, True),
            ]
        )
        self._prompt = prompt

    def _download(self, prompt: Prompt, release: updates.Release) -> None:
        staged = Path(tempfile.mkdtemp(prefix="carol_aio_update_")) / release.asset_name
        prompt.lock(True)
        prompt.set_status("Downloading...")
        prompt.set_progress(0.0)
        last = [-1]

        def progress(received: int, total: int) -> None:
            percent = received * 100 // total if total else 0
            if percent != last[0]:
                last[0] = percent
                self.post(lambda: prompt.set_progress(percent / 100))

        def work() -> None:
            try:
                updates.download(release, staged, progress)
            except updates.UpdateError as exc:
                self.post(lambda: self._failed(prompt, release, str(exc)))
            else:
                self.post(lambda: self._downloaded(prompt, staged))

        threading.Thread(target=work, daemon=True).start()

    def _downloaded(self, prompt: Prompt, staged: Path) -> None:
        prompt.destroy()
        self.on_update(staged)

    def _failed(self, prompt: Prompt, release: updates.Release, message: str) -> None:
        prompt.set_progress(None)
        prompt.set_status(message, fault=True)
        prompt.lock(False)
        prompt.set_choices(
            [
                Choice("Close"),
                Choice("Try again", lambda: self._download(prompt, release), True, True),
            ]
        )
