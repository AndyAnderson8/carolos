import tempfile
import unittest
from pathlib import Path
from unittest import mock

from carol_aio import install


class IsInstalledTest(unittest.TestCase):
    def test_source_runs_are_not_installed(self) -> None:
        self.assertFalse(install.is_installed())

    def test_installed_when_the_uninstaller_sits_beside_the_exe(self) -> None:
        folder = Path(tempfile.mkdtemp())
        exe = folder / "CarolAIO.exe"
        exe.write_text("")
        with mock.patch.object(install, "running_exe", return_value=exe):
            self.assertFalse(install.is_installed())
            (folder / install.UNINSTALLER).write_text("")
            self.assertTrue(install.is_installed())


class RunSetupTest(unittest.TestCase):
    def test_runs_the_installer_silently_and_detached(self) -> None:
        with mock.patch("subprocess.Popen") as popen:
            install.run_setup(Path(r"C:\temp\CarolAIO-Setup-v1.exe"))
        args, kwargs = popen.call_args
        self.assertEqual(args[0][0], r"C:\temp\CarolAIO-Setup-v1.exe")
        self.assertIn("/SILENT", args[0])
        self.assertIn("/NORESTART", args[0])
        self.assertEqual(kwargs["creationflags"], install.DETACHED)


if __name__ == "__main__":
    unittest.main()
