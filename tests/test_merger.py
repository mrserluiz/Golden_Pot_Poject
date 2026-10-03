from __future__ import annotations

import tempfile
import unittest
import json
import zipfile
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
            (base / "manifest.json").write_text(json.dumps({
                "format_version": 2,
                "header": {"name": "mine", "uuid": "11111111-1111-1111-1111-111111111111", "version": [1, 0, 0]},
                "modules": [{"type": "resources", "uuid": "22222222-2222-2222-2222-222222222222", "version": [1, 0, 0]}],
            }), encoding="utf-8")
            (comparison / "manifest.json").write_text("{}", encoding="utf-8")
            result = create_merged_folder(compare_directories(base, comparison), output)
            self.assertEqual((output / "keep.txt").read_text(), "custom")
            self.assertEqual((output / "change.txt").read_text(), "new")
            self.assertEqual((output / "add.txt").read_text(), "added")
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["header"]["uuid"], "11111111-1111-1111-1111-111111111111")
            self.assertEqual(manifest["header"]["version"], [1, 0, 1])
            with zipfile.ZipFile(output / "pack.zip") as archive:
                self.assertIn("manifest.json", archive.namelist())
                self.assertIn("keep.txt", archive.namelist())
            self.assertEqual(result.added_from_comparison, 1)
            self.assertEqual(result.updated_from_comparison, 1)
            self.assertEqual(result.protected_from_base, 0)

    def test_merges_geyser_mappings_and_validates_texture_paths(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            base, comparison, output = root / "base", root / "rainbow", root / "result"
            for folder in (base, comparison):
                (folder / "custom_mappings").mkdir(parents=True)
                (folder / "textures" / "items").mkdir(parents=True)
            (base / "manifest.json").write_text("{}")
            (base / "custom_mappings" / "items.json").write_text(json.dumps({
                "format_version": 2,
                "items": {"minecraft:flint": [{"type": "definition", "model": "old:item", "bedrock_identifier": "old:item"}]},
            }))
            (comparison / "custom_mappings" / "items.json").write_text(json.dumps({
                "format_version": 2,
                "items": {"minecraft:flint": [{"type": "definition", "model": "new:item", "bedrock_identifier": "new:item"}]},
            }))
            (base / "textures" / "item_texture.json").write_text(json.dumps({
                "texture_data": {"old.item": {"textures": "textures/items/old"}}
            }))
            (comparison / "textures" / "item_texture.json").write_text(json.dumps({
                "texture_data": {"new.item": {"textures": "textures/items/new"}}
            }))
            (base / "textures" / "items" / "old.png").write_bytes(b"old")
            (comparison / "textures" / "items" / "new.png").write_bytes(b"new")

            result = create_merged_folder(compare_directories(base, comparison), output)
            mapping = json.loads((output / "custom_mappings" / "items.json").read_text())
            identifiers = {entry["bedrock_identifier"] for entry in mapping["items"]["minecraft:flint"]}
            self.assertEqual(identifiers, {"old:item", "new:item"})
            registry = json.loads((output / "textures" / "item_texture.json").read_text())
            self.assertEqual(set(registry["texture_data"]), {"old.item", "new.item"})
            self.assertEqual(result.merged_json_files, 2)
            self.assertFalse(result.warnings)
            with zipfile.ZipFile(output / "pack.zip") as archive:
                self.assertIn("textures/items/old.png", archive.namelist())
                self.assertIn("textures/items/new.png", archive.namelist())
                self.assertNotIn("custom_mappings/items.json", archive.namelist())

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
