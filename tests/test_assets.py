import unittest
from pathlib import Path


class AssetTests(unittest.TestCase):
    def test_visual_assets_are_packaged(self) -> None:
        assets = Path(__file__).parents[1] / "src" / "golden_pot" / "assets"
        for name in ("icon1.png", "icon1.ico", "icon2.png", "cloud.png"):
            path = assets / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 0, name)


if __name__ == "__main__":
    unittest.main()
