from __future__ import annotations

import os
import shutil
import tempfile
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .models import ComparisonReport, FileStatus
from .structured_merge import (
    is_mapping_path,
    is_pack_registry,
    merge_json_files,
    read_json,
    update_manifest,
)


@dataclass(frozen=True, slots=True)
class MergeResult:
    output_folder: Path
    copied_from_base: int
    added_from_comparison: int
    updated_from_comparison: int
    protected_from_base: int
    merged_json_files: int = 0
    rebuilt_pack: Path | None = None
    warnings: tuple[str, ...] = ()


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def create_merged_folder(report: ComparisonReport, output_folder: str | Path) -> MergeResult:
    """Create a new pack from the base and safely overlay comparison changes."""
    base_root = Path(report.base_folder).resolve()
    comparison_root = Path(report.comparison_folder).resolve()
    output_root = Path(output_folder).expanduser().resolve()

    for source in (base_root, comparison_root):
        if output_root == source or _contains(source, output_root) or _contains(output_root, source):
            raise ValueError("Output folder must be separate from both source folders")
    if output_root.exists() and (not output_root.is_dir() or any(output_root.iterdir())):
        raise FileExistsError("Output folder already exists and is not empty")

    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-", dir=output_root.parent))
    copied_from_base = added = updated = protected = merged_json = 0
    warnings: list[str] = []
    try:
        for item in report.items:
            if item.status == FileStatus.ERROR:
                raise OSError(f"Cannot merge file with scan error: {item.relative_path}")
            relative = Path(*item.relative_path.split("/"))
            target = temporary_root / relative
            normalized = item.relative_path.casefold()
            if normalized in {"pack.zip", "manifest.json"}:
                if normalized == "manifest.json" and item.status == FileStatus.PROTECTED:
                    protected += 1
                continue
            if (
                item.status in (FileStatus.MODIFIED, FileStatus.PROTECTED)
                and (is_mapping_path(item.relative_path) or is_pack_registry(item.relative_path))
            ):
                try:
                    merge_json_files(base_root / relative, comparison_root / relative, target)
                    merged_json += 1
                    continue
                except (OSError, json.JSONDecodeError, TypeError) as error:
                    warnings.append(f"Could not merge {item.relative_path}: {error}; current file used")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(comparison_root / relative, target)
                    updated += 1
                    continue
            if item.status in (FileStatus.UNCHANGED, FileStatus.PRESERVED, FileStatus.PROTECTED):
                source = base_root / relative
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    copied_from_base += 1
                    protected += item.status == FileStatus.PROTECTED
            elif item.status in (FileStatus.ADDED, FileStatus.MODIFIED):
                source = comparison_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                if item.status == FileStatus.ADDED:
                    added += 1
                else:
                    updated += 1

        base_manifest = base_root / "manifest.json"
        current_manifest = comparison_root / "manifest.json"
        update_manifest(
            base_manifest if base_manifest.is_file() else None,
            current_manifest if current_manifest.is_file() else None,
            temporary_root / "manifest.json",
        )
        warnings.extend(_validate_mapping_textures(temporary_root))
        _write_merge_report(temporary_root, merged_json, warnings)
        _build_pack_zip(temporary_root)
        if output_root.exists():
            output_root.rmdir()
        os.replace(temporary_root, output_root)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return MergeResult(
        output_root, copied_from_base, added, updated, protected,
        merged_json, output_root / "pack.zip", tuple(warnings),
    )


def _mapping_files(root: Path) -> list[Path]:
    return [
        path for path in root.rglob("*.json")
        if is_mapping_path(path.relative_to(root).as_posix())
    ]


def _walk_definitions(value: object):
    if isinstance(value, dict):
        if "bedrock_identifier" in value or "bedrock_options" in value:
            yield value
        for child in value.values():
            yield from _walk_definitions(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_definitions(child)


def _validate_mapping_textures(root: Path) -> list[str]:
    warnings: list[str] = []
    registry_path = root / "textures" / "item_texture.json"
    texture_data: dict[str, object] = {}
    if registry_path.is_file():
        try:
            registry = read_json(registry_path)
            if isinstance(registry, dict) and isinstance(registry.get("texture_data"), dict):
                texture_data = registry["texture_data"]
        except (OSError, json.JSONDecodeError):
            warnings.append("Invalid textures/item_texture.json")

    identifiers: dict[str, str] = {}
    for mapping_path in _mapping_files(root):
        try:
            mapping = read_json(mapping_path)
        except (OSError, json.JSONDecodeError) as error:
            warnings.append(f"Invalid mapping JSON {mapping_path.relative_to(root).as_posix()}: {error}")
            continue
        for definition in _walk_definitions(mapping):
            identifier = definition.get("bedrock_identifier")
            if isinstance(identifier, str):
                if identifier in identifiers:
                    warnings.append(f"Duplicate bedrock_identifier: {identifier}")
                identifiers[identifier] = mapping_path.relative_to(root).as_posix()
            options = definition.get("bedrock_options")
            icon = options.get("icon") if isinstance(options, dict) else None
            if not isinstance(icon, str) and isinstance(identifier, str):
                icon = identifier.replace(":", ".").replace("/", "_")
            if isinstance(icon, str) and icon not in texture_data:
                warnings.append(f"Mapping icon has no item_texture entry: {icon}")

    for key, entry in texture_data.items():
        values = entry.get("textures") if isinstance(entry, dict) else None
        paths = values if isinstance(values, list) else [values]
        for texture in paths:
            if not isinstance(texture, str):
                continue
            candidate = root / texture.replace("\\", "/")
            if candidate.suffix:
                exists = candidate.is_file()
            else:
                exists = any(candidate.with_suffix(extension).is_file() for extension in (".png", ".tga", ".jpg", ".jpeg"))
            if not exists:
                warnings.append(f"Texture path does not exist for {key}: {texture}")
    return warnings


def _write_merge_report(root: Path, merged_json: int, warnings: list[str]) -> None:
    lines = [
        "Golden Pot semantic merge report",
        f"Merged mapping/registry JSON files: {merged_json}",
        f"Warnings: {len(warnings)}",
        "",
        *(warnings or ["No mapping or texture reference warnings."]),
    ]
    (root / "golden-pot-merge-report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_pack_zip(root: Path) -> None:
    destination = root / "pack.zip"
    excluded_names = {"pack.zip", "report.txt", "golden-pot-merge-report.txt"}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.casefold() in excluded_names:
                continue
            relative = path.relative_to(root)
            if relative.parts and (
                relative.parts[0].casefold().startswith("custom_mappings")
                or relative.parts[0].casefold() == "lang"
            ):
                continue
            archive.write(path, relative.as_posix())
