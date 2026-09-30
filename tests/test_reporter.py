from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from golden_pot.comparator import compare_directories
from golden_pot.reporter import write_reports


class ReporterTests(unittest.TestCase):
    def test_writes_json_and_text_reports(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base = root / "base"
            comparison = root / "comparison"
            output = root / "reports"
            base.mkdir()
            comparison.mkdir()
            (comparison / "new.txt").write_text("new", encoding="utf-8")

            report = compare_directories(base, comparison)
            json_path, text_path = write_reports(report, output, basename="test")

            self.assertTrue(json_path.is_file())
            self.assertTrue(text_path.is_file())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["ADDED"], 1)
            self.assertIn("ADDED: 1", text_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
