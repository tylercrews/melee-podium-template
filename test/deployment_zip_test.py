"""Release packaging always builds the current frontend before archiving it."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import build_deployment_zip as deployment


class DeploymentZipTest(unittest.TestCase):
    def test_frontend_build_runs_in_frontend_directory(self):
        with patch.object(deployment.shutil, "which", return_value="npm.cmd"), patch.object(
            deployment.subprocess, "run"
        ) as run:
            deployment.build_frontend()
        run.assert_called_once_with(
            ["npm.cmd", "run", "build"], cwd=deployment.ROOT / "frontend", check=True
        )

    def test_missing_npm_stops_packaging(self):
        with patch.object(deployment.shutil, "which", return_value=None), patch.object(
            deployment, "create_archive"
        ) as archive:
            with self.assertRaisesRegex(RuntimeError, "npm is required"):
                deployment.main()
        archive.assert_not_called()

    def test_failed_frontend_build_stops_packaging(self):
        with patch.object(
            deployment, "build_frontend", side_effect=subprocess.CalledProcessError(1, "npm")
        ), patch.object(deployment, "create_archive") as archive:
            with self.assertRaises(subprocess.CalledProcessError):
                deployment.main()
        archive.assert_not_called()

    def test_archive_contains_newly_built_frontend_and_excludes_private_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "frontend" / "dist"
            dist.mkdir(parents=True)
            (dist / "index.html").write_text("old footer", encoding="utf-8")
            (root / "app.py").write_text("# server", encoding="utf-8")
            (root / ".env").write_text("private configuration", encoding="utf-8")
            (root / "podium_stats.sqlite3").write_bytes(b"private stats")
            (dist / "__pycache__").mkdir()
            (dist / "__pycache__" / "ignored.pyc").write_bytes(b"cache")

            def rebuild():
                (dist / "index.html").write_text("current footer", encoding="utf-8")

            archive_path = root / "release.zip"
            with patch.multiple(
                deployment, ROOT=root, ARCHIVE=archive_path,
                FILES=("app.py",), DIRECTORIES=("frontend/dist",),
            ), patch.object(deployment, "build_frontend", side_effect=rebuild), patch("builtins.print"):
                deployment.main()

            with ZipFile(archive_path) as archive:
                self.assertEqual(set(archive.namelist()), {"app.py", "frontend/dist/index.html"})
                self.assertEqual(archive.read("frontend/dist/index.html"), b"current footer")


if __name__ == "__main__":
    unittest.main()
