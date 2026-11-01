import hashlib
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from carolos import updates
from carolos.updates import Release, UpdateError

SAMPLE = {
    "tag_name": "v1.2.0",
    "body": "Fixes things.",
    "html_url": "https://example.test/release",
    "assets": [
        {"name": "notes.txt", "browser_download_url": "https://example.test/notes"},
        {
            "name": "CaroLOS-Setup-v1.2.0.exe",
            "browser_download_url": "https://example.test/CaroLOS.exe",
            "size": 5,
            "digest": "sha256:" + hashlib.sha256(b"hello").hexdigest(),
        },
    ],
}


def release(version: str = "v1.2.0") -> Release:
    return Release(version, "", "", "https://example.test/x", "x.exe", 5, None)


class ParseVersionTest(unittest.TestCase):
    def test_tags_and_plain_numbers(self) -> None:
        self.assertEqual(updates.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(updates.parse_version("10.0.1"), (10, 0, 1))

    def test_commits_and_dev_are_not_versions(self) -> None:
        self.assertIsNone(updates.parse_version("04d6a46"))
        self.assertIsNone(updates.parse_version("dev"))


class NewerThanTest(unittest.TestCase):
    def test_compares_numbers_not_text(self) -> None:
        self.assertTrue(updates.newer_than(release("v1.10.0"), "v1.9.0"))
        self.assertFalse(updates.newer_than(release("v1.2.0"), "v1.3.0"))

    def test_same_version_is_not_an_update(self) -> None:
        self.assertFalse(updates.newer_than(release("v1.2.0"), "v1.2.0"))

    def test_source_runs_never_update(self) -> None:
        self.assertFalse(updates.newer_than(release(), "dev"))

    def test_commit_builds_ask_github_which_is_newer(self) -> None:
        with mock.patch.object(updates, "_is_ahead", return_value=True) as ahead:
            self.assertTrue(updates.newer_than(release("v1.2.0"), "04d6a46"))
        ahead.assert_called_once_with("04d6a46", "v1.2.0")
        with mock.patch.object(updates, "_is_ahead", return_value=False):
            self.assertFalse(updates.newer_than(release("v1.2.0"), "04d6a46"))


class LatestReleaseTest(unittest.TestCase):
    def test_reads_the_exe_asset(self) -> None:
        with mock.patch.object(updates, "_get", return_value=SAMPLE):
            found = updates.latest_release()
        assert found is not None
        self.assertEqual(found.version, "v1.2.0")
        self.assertEqual(found.asset_name, "CaroLOS-Setup-v1.2.0.exe")
        self.assertEqual(found.size, 5)
        self.assertEqual(found.sha256, hashlib.sha256(b"hello").hexdigest())

    def test_no_exe_attached_means_no_update(self) -> None:
        data = {**SAMPLE, "assets": [SAMPLE["assets"][0]]}
        with mock.patch.object(updates, "_get", return_value=data):
            self.assertIsNone(updates.latest_release())

    def test_a_bare_exe_is_not_the_installer(self) -> None:
        data = {
            **SAMPLE,
            "assets": [{"name": "CaroLOS-v1.2.0.exe", "browser_download_url": "https://x"}],
        }
        with mock.patch.object(updates, "_get", return_value=data):
            self.assertIsNone(updates.latest_release())

    def test_404_means_nothing_published(self) -> None:
        error = urllib.error.HTTPError("u", 404, "Not Found", {}, None)  # type: ignore[arg-type]
        with mock.patch.object(updates, "_get", side_effect=error):
            self.assertIsNone(updates.latest_release())

    def test_network_failure_is_a_readable_error(self) -> None:
        with mock.patch.object(updates, "_get", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(UpdateError):
                updates.latest_release()

    def test_long_notes_are_trimmed(self) -> None:
        data = {**SAMPLE, "body": "x" * 2000}
        with mock.patch.object(updates, "_get", return_value=data):
            found = updates.latest_release()
        assert found is not None
        self.assertLess(len(found.notes), 600)

    def test_check_reports_latest_even_when_up_to_date(self) -> None:
        with mock.patch.object(updates, "_get", return_value=SAMPLE):
            result = updates.check("v1.2.0")
        self.assertIsNone(result.update)
        self.assertEqual(result.latest, "v1.2.0")


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self) -> "FakeResponse":
        return self


class DownloadTest(unittest.TestCase):
    def fetch(self, data: bytes, sha: str | None, size: int) -> Path:
        item = Release("v1", "", "", "https://example.test/x", "x.exe", size, sha)
        dest = Path(tempfile.mkdtemp()) / "x.exe.new"
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(data)):
            updates.download(item, dest, lambda received, total: None)
        return dest

    def test_good_download_is_kept(self) -> None:
        dest = self.fetch(b"hello", hashlib.sha256(b"hello").hexdigest(), 5)
        self.assertEqual(dest.read_bytes(), b"hello")

    def test_wrong_checksum_is_rejected_and_removed(self) -> None:
        dest = Path(tempfile.mkdtemp()) / "x.exe.new"
        item = Release("v1", "", "", "https://example.test/x", "x.exe", 5, "0" * 64)
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b"hello")):
            with self.assertRaises(UpdateError):
                updates.download(item, dest, lambda received, total: None)
        self.assertFalse(dest.exists())

    def test_wrong_size_is_rejected(self) -> None:
        with self.assertRaises(UpdateError):
            self.fetch(b"hello", None, 99)


if __name__ == "__main__":
    unittest.main()
