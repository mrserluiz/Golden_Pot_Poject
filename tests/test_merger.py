from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from golden_pot.comparator import compare_directories
from golden_pot.merger import create_merged_folder


class MergerTests(unittest.TestCase):
    def test_safe_merge_adds_updates_and_preserves(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base, comparison, output = root / "base", root / "rainbow", root / "result"
            base.mkdir(); comparison.mkdir()
            (base / "keep.txt").write_text("custom", encoding="utf-8")
            (base / "change.txt").write_text("old", encoding="utf-8")
            (comparison / "change.txt").write_text("new", encoding="utf-8")
            (comparison / "add.txt").write_text("added", encoding="utf-8")
            (base / "manifest.json").write_text("mine", encoding="utf-8")
            (comparison / "manifest.json").write_text("rainbow", encoding="utf-8")
            result = create_merged_folder(compare_directories(base, comparison), output)
            self.assertEqual((output / "keep.txt").read_text(), "custom")
            self.assertEqual((output / "change.txt").read_text(), "new")
            self.assertEqual((output / "add.txt").read_text(), "added")
            self.assertEqual((output / "manifest.json").read_text(), "mine")
            self.assertEqual(result.added_from_comparison, 1)
            self.assertEqual(result.updated_from_comparison, 1)
            self.assertEqual(result.protected_from_base, 1)

    def test_non_empty_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base, comparison, output = root / "base", root / "rainbow", root / "result"
            base.mkdir(); comparison.mkdir(); output.mkdir()
            (output / "existing.txt").write_text("do not overwrite")
            with self.assertRaises(FileExistsError):
                create_merged_folder(compare_directories(base, comparison), output)


if __name__ == "__main__":
    unittest.main()
