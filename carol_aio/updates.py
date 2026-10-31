"""Find and download new releases from GitHub.

CI publishes ``CarolAIO-Setup-<version>.exe`` on every release. This reads the latest
published (non-pre-release) one from the public Releases API.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = "AndyAnderson8/carol-aio"
API = os.environ.get("CAROL_AIO_API", f"https://api.github.com/repos/{REPO}")  # override: tests
TIMEOUT = 10
CHUNK = 64 * 1024
NOTES_LIMIT = 500


class UpdateError(Exception):
    """Something went wrong reaching GitHub or downloading; the message is fit to show."""


@dataclass(frozen=True)
class Release:
    version: str  # the tag, e.g. "v1.2.0"
    notes: str
    page: str
    asset_url: str
    asset_name: str
    size: int
    sha256: str | None


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text.strip())
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def _is_installer(name: str) -> bool:
    """The Setup program CI attaches to each release (CarolAIO-Setup-<version>.exe)."""
    return name.lower().endswith(".exe") and "setup" in name.lower()


def _get(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CarolAIO-updater"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def latest_release() -> Release | None:
    """The newest published release with an exe attached, or None if there isn't one."""
    try:
        data = _get(f"{API}/releases/latest")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None  # no releases yet (or the repo isn't public)
        raise UpdateError(f"GitHub answered with an error ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpdateError("Couldn't reach GitHub. Check your internet connection.") from exc
    asset = next(
        (a for a in data.get("assets", []) if _is_installer(str(a.get("name", "")))),
        None,
    )
    if asset is None:
        return None
    digest = str(asset.get("digest") or "")
    notes = str(data.get("body") or "").strip()
    return Release(
        version=str(data["tag_name"]),
        notes=notes if len(notes) <= NOTES_LIMIT else notes[:NOTES_LIMIT].rstrip() + "...",
        page=str(data.get("html_url", "")),
        asset_url=str(asset["browser_download_url"]),
        asset_name=str(asset["name"]),
        size=int(asset.get("size") or 0),
        sha256=digest.removeprefix("sha256:") if digest.startswith("sha256:") else None,
    )


def _is_ahead(current_commit: str, release_tag: str) -> bool:
    """Whether ``release_tag`` is newer than a commit-hash build (asks GitHub to compare)."""
    try:
        data = _get(f"{API}/compare/{current_commit}...{release_tag}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    return bool(data.get("status") == "ahead")


def newer_than(release: Release, current: str) -> bool:
    """Whether ``release`` should be offered to someone running ``current``."""
    if release.version == current or current == "dev":
        return False
    latest, running = parse_version(release.version), parse_version(current)
    if latest and running:
        return latest > running
    return _is_ahead(current, release.version)  # a commit-hash build: compare by history


@dataclass(frozen=True)
class CheckResult:
    update: Release | None  # the release to offer, or None when current is up to date
    latest: str | None  # the newest published version, or None if nothing is published


def check(current: str) -> CheckResult:
    release = latest_release()
    if release is None:
        return CheckResult(None, None)
    return CheckResult(release if newer_than(release, current) else None, release.version)


def download(release: Release, dest: Path, progress: Callable[[int, int], None]) -> None:
    """Download the release exe to ``dest``, checking its size and checksum."""
    request = urllib.request.Request(release.asset_url, headers={"User-Agent": "CarolAIO-updater"})
    digest = hashlib.sha256()
    received = 0
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response, dest.open("wb") as out:
            total = int(response.headers.get("Content-Length") or release.size)
            while chunk := response.read(CHUNK):
                out.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                progress(received, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        dest.unlink(missing_ok=True)
        raise UpdateError("The download was interrupted. Try again in a moment.") from exc
    if (release.size and received != release.size) or (
        release.sha256 and digest.hexdigest() != release.sha256
    ):
        dest.unlink(missing_ok=True)
        raise UpdateError("The download didn't match what GitHub published. Try again.")
