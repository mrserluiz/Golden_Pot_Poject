from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from golden_pot.comparator import compare_directories
from golden_pot.config import GoldenPotConfig
from golden_pot.models import FileStatus


class ComparatorTests(unittest.TestCase):
    def test_all_core_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = root / "base"
            comparison = root / "comparison"
            base.mkdir()
            comparison.mkdir()

            (base / "same.txt").write_text("same", encoding="utf-8")
            (comparison / "same.txt").write_text("same", encoding="utf-8")
            (base / "changed.txt").write_text("old", encoding="utf-8")
            (comparison / "changed.txt").write_text("new", encoding="utf-8")
            (base / "old.txt").write_text("keep", encoding="utf-8")
            (comparison / "new.txt").write_text("add", encoding="utf-8")
            (base / "manifest.json").write_text("old", encoding="utf-8")
            (comparison / "manifest.json").write_text("new", encoding="utf-8")

            report = compare_directories(base, comparison, GoldenPotConfig())
            statuses = {item.relative_path: item.status for item in report.items}

            self.assertEqual(statuses["same.txt"], FileStatus.UNCHANGED)
            self.assertEqual(statuses["changed.txt"], FileStatus.MODIFIED)
            self.assertEqual(statuses["old.txt"], FileStatus.PRESERVED)
            self.assertEqual(statuses["new.txt"], FileStatus.ADDED)
            self.assertEqual(statuses["manifest.json"], FileStatus.PROTECTED)

    def test_same_folder_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            with self.assertRaises(ValueError):
                compare_directories(workspace, workspace)

    def test_ignored_directory_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = root / "base"
            comparison = root / "comparison"
            (base / ".git").mkdir(parents=True)
            comparison.mkdir()
            (base / ".git" / "config").write_text("secret", encoding="utf-8")

            report = compare_directories(base, comparison, GoldenPotConfig())
            self.assertEqual(report.items, [])


if __name__ == "__main__":
    unittest.main()
