from __future__ import annotations

import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _unwrap(root: Path) -> Path:
    current = root
    for _ in range(3):
        if (current / "pack.zip").is_file() or (current / "manifest.json").is_file():
            return current
        children = [path for path in current.iterdir() if path.is_dir()]
        files = [path for path in current.iterdir() if path.is_file()]
        if len(children) == 1 and not files:
            current = children[0]
        else:
            break
    return current


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        destination_resolved = destination.resolve()
        for entry in archive.infolist():
            target = (destination / entry.filename).resolve()
            if target != destination_resolved and destination_resolved not in target.parents:
                raise ValueError(f"Unsafe ZIP entry: {entry.filename}")
        archive.extractall(destination)


@contextmanager
def normalized_source(selected_folder: str | Path) -> Iterator[Path]:
    """Expose a normal pack root for plain packs and Rainbow output bundles."""
    selected = Path(selected_folder).expanduser().resolve()
    root = _unwrap(selected)
    if root.name.casefold().startswith("pack.") and (root.parent / "pack.zip").is_file():
        root = root.parent
    if (root / "manifest.json").is_file():
        yield root
        return

    pack_zip = root / "pack.zip"
    pack_directories = sorted(
        path for path in root.iterdir()
        if path.is_dir() and path.name.casefold().startswith("pack.")
    )
    if not pack_zip.is_file() and len(pack_directories) != 1:
        yield selected
        return

    with tempfile.TemporaryDirectory(prefix="golden-pot-source-") as temporary:
        staging = Path(temporary)
        if pack_zip.is_file():
            _safe_extract(pack_zip, staging)
        else:
            shutil.copytree(pack_directories[0], staging, dirs_exist_ok=True)
        for child in root.iterdir():
            name = child.name.casefold()
            if child.is_dir() and (name.startswith("custom_mappings") or name == "lang"):
                shutil.copytree(child, staging / child.name, dirs_exist_ok=True)
        yield staging
