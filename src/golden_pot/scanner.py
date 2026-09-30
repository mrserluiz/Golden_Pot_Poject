from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .models import FileSnapshot


READ_BUFFER_SIZE = 1024 * 1024


def matches_rule(relative_path: str, rule: str) -> bool:
    normalized_path = relative_path.replace("\\", "/").lstrip("./")
    normalized_rule = rule.replace("\\", "/").lstrip("./")
    if normalized_rule.endswith("/"):
        directory = normalized_rule.rstrip("/")
        return normalized_path == directory or normalized_path.startswith(directory + "/")
    return normalized_path == normalized_rule


def is_ignored(relative_path: str, ignored_paths: tuple[str, ...]) -> bool:
    return any(matches_rule(relative_path, rule) for rule in ignored_paths)


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(READ_BUFFER_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def scan_directory(
    root: str | Path,
    *,
    algorithm: str = "sha256",
    ignored_paths: tuple[str, ...] = (),
) -> dict[str, FileSnapshot]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Folder does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root_path}")

    snapshots: dict[str, FileSnapshot] = {}
    for current_root, directory_names, file_names in os.walk(root_path):
        current_path = Path(current_root)
        directory_names[:] = sorted(
            directory
            for directory in directory_names
            if not is_ignored(
                (current_path / directory).relative_to(root_path).as_posix() + "/",
                ignored_paths,
            )
        )

        for filename in sorted(file_names):
            absolute_path = current_path / filename
            relative_path = absolute_path.relative_to(root_path).as_posix()
            if is_ignored(relative_path, ignored_paths):
                continue
            try:
                if absolute_path.is_symlink():
                    raise OSError("Symbolic links are not followed in v0.1")
                size = absolute_path.stat().st_size
                digest = hash_file(absolute_path, algorithm)
                snapshot = FileSnapshot(relative_path, absolute_path, size, digest)
            except OSError as error:
                snapshot = FileSnapshot(
                    relative_path,
                    absolute_path,
                    None,
                    None,
                    f"{type(error).__name__}: {error}",
                )
            snapshots[relative_path] = snapshot
    return snapshots
