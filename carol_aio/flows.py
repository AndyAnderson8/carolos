"""The update notices, and what each button does."""

from __future__ import annotations

import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from carol_aio import __version__, install, updates
from carol_aio.pages import Choice, NoticePage

Post = Callable[[Callable[[], None]], None]  # run something on the Tk thread


class NoticeHost(Protocol):
    """Where notices appear: the tray panel."""

    def show_notice(
        self, title: str, message: str, choices: list[Choice], detail: str = ""
    ) -> NoticePage: ...

    def notice_open(self) -> bool: ...

    def show(self) -> None: ...


class Updater:
    """Checks GitHub for a newer release and walks through downloading its installer.

    Once the installer is downloaded it hands the file to ``on_update``; the app
    then quits and runs it, and the installer replaces the app and relaunches it.
    """

    def __init__(self, host: NoticeHost, post: Post, on_update: Callable[[Path], None]) -> None:
        self.host, self.post, self.on_update = host, post, on_update
        self._busy = False

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
        if self._busy or self.host.notice_open():
            self.host.show()
            return
        self._busy = True
        if manual:
            self.host.show_notice("Updates", "Checking for updates...", [Choice("Close")])
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

    def _tell(self, title: str, message: str) -> None:
        self.host.show_notice(title, message, [Choice("OK", primary=True)])

    def _offer(self, release: updates.Release) -> None:
        self.host.show_notice(
            "Update available",
            f"Carol AIO {release.version} is ready. You have {__version__}.",
            [
                Choice("Later"),
                Choice("Update now", lambda: self._download(release), True, True),
            ],
            detail=release.notes,
        )

    def _download(self, release: updates.Release) -> None:
        page = self.host.show_notice(
            "Updating",
            f"Downloading Carol AIO {release.version}...",
            [Choice("Update now", primary=True, keep_open=True)],
        )
        page.set_choices([Choice("Update now", primary=True, keep_open=True)])
        page.lock(True)
        page.set_progress(0.0)
        staged = Path(tempfile.mkdtemp(prefix="carol_aio_update_")) / release.asset_name
        last = [-1]

        def progress(received: int, total: int) -> None:
            percent = received * 100 // total if total else 0
            if percent != last[0]:
                last[0] = percent
                self.post(lambda: page.set_progress(percent / 100))

        def work() -> None:
            try:
                updates.download(release, staged, progress)
            except updates.UpdateError as exc:
                self.post(lambda: self._failed(release, str(exc)))
            else:
                self.post(lambda: self.on_update(staged))

        threading.Thread(target=work, daemon=True).start()

    def _failed(self, release: updates.Release, message: str) -> None:
        page = self.host.show_notice(
            "Couldn't update",
            message,
            [
                Choice("Close"),
                Choice("Try again", lambda: self._download(release), True, True),
            ],
        )
