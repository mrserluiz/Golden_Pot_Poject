import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from golden_pot.source_adapter import normalized_source


class SourceAdapterTests(unittest.TestCase):
    def test_opens_rainbow_bundle_pack_and_mappings_as_one_source(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace) / "T05"
            root.mkdir()
            with zipfile.ZipFile(root / "pack.zip", "w") as archive:
                archive.writestr("manifest.json", json.dumps({"format_version": 2}))
                archive.writestr("textures/items/example.png", b"png")
            mappings = root / "custom_mappings_example"
            mappings.mkdir()
            (mappings / "items.json").write_text('{"format_version": 2, "items": {}}')

            with normalized_source(root) as normalized:
                self.assertTrue((normalized / "manifest.json").is_file())
                self.assertTrue((normalized / "textures" / "items" / "example.png").is_file())
                self.assertTrue((normalized / "custom_mappings_example" / "items.json").is_file())


if __name__ == "__main__":
    unittest.main()
