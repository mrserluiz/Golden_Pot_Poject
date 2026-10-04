from __future__ import annotations

import os
import shutil
import tempfile
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .models import ComparisonReport, FileStatus
from .structured_merge import is_mapping_path, is_pack_registry, merge_json_files, read_json, update_manifest

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

@dataclass(frozen=True, slots=True)
class LayeredMergeResult:
    output_folder: Path
    texture: MergeResult
    mappings_folder: Path
    preserved_mappings: int
    added_mappings: int
    updated_mappings: int
    merged_mapping_files: int
    rebuilt_pack: Path
    warnings: tuple[str, ...] = ()

def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False

def create_merged_folder(report: ComparisonReport, output_folder: str | Path) -> MergeResult:
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
            if item.status in (FileStatus.MODIFIED, FileStatus.PROTECTED) and (is_mapping_path(item.relative_path) or is_pack_registry(item.relative_path)):
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
                if item.status == FileStatus.ADDED: added += 1
                else: updated += 1
        base_manifest = base_root / "manifest.json"
        current_manifest = comparison_root / "manifest.json"
        update_manifest(base_manifest if base_manifest.is_file() else None, current_manifest if current_manifest.is_file() else None, temporary_root / "manifest.json")
        warnings.extend(_validate_mapping_textures(temporary_root))
        _write_merge_report(temporary_root, merged_json, warnings)
        _build_pack_zip(temporary_root)
        if output_root.exists(): output_root.rmdir()
        os.replace(temporary_root, output_root)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return MergeResult(output_root, copied_from_base, added, updated, protected, merged_json, output_root / "pack.zip", tuple(warnings))

def create_layered_package(texture_report: ComparisonReport, base_mappings: str | Path, current_mappings: str | Path, output_folder: str | Path) -> LayeredMergeResult:
    """Merge texture and mapping layers independently; a missing new file never deletes old work."""
    output_root = Path(output_folder).expanduser().resolve()
    mapping_base = Path(base_mappings).expanduser().resolve()
    mapping_current = Path(current_mappings).expanduser().resolve()
    sources = (Path(texture_report.base_folder).resolve(), Path(texture_report.comparison_folder).resolve(), mapping_base, mapping_current)
    for source in sources:
        if output_root == source or _contains(source, output_root) or _contains(output_root, source):
            raise ValueError("Output folder must be separate from all source folders")
    if output_root.exists() and (not output_root.is_dir() or any(output_root.iterdir())):
        raise FileExistsError("Output folder already exists and is not empty")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-", dir=output_root.parent))
    try:
        texture_result = create_merged_folder(texture_report, temporary_root / "pack")
        os.replace(temporary_root / "pack" / "pack.zip", temporary_root / "pack.zip")
        (temporary_root / "pack" / "golden-pot-merge-report.txt").unlink(missing_ok=True)
        mappings_root = temporary_root / "custom_mappings"
        preserved, added, updated, merged = _merge_mapping_layers(mapping_base, mapping_current, mappings_root)
        warnings = list(texture_result.warnings)
        warnings.extend(_validate_mapping_textures(temporary_root / "pack", mappings_root))
        reports_root = temporary_root / "reports"
        reports_root.mkdir()
        _write_layered_report(reports_root / "golden-pot-layered-merge.txt", preserved, added, updated, merged, warnings)
        if output_root.exists(): output_root.rmdir()
        os.replace(temporary_root, output_root)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return LayeredMergeResult(output_root, texture_result, output_root / "custom_mappings", preserved, added, updated, merged, output_root / "pack.zip", tuple(warnings))

def _merge_mapping_layers(previous: Path, current: Path, destination: Path) -> tuple[int, int, int, int]:
    previous_files = {p.relative_to(previous).as_posix(): p for p in previous.rglob("*") if p.is_file()}
    current_files = {p.relative_to(current).as_posix(): p for p in current.rglob("*") if p.is_file()}
    preserved = added = updated = merged = 0
    for relative_name in sorted(set(previous_files) | set(current_files), key=str.casefold):
        old, new = previous_files.get(relative_name), current_files.get(relative_name)
        target = destination / Path(*relative_name.split("/"))
        if old and new and relative_name.casefold().endswith(".json"):
            try:
                merge_json_files(old, new, target)
                merged += 1
                continue
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        target.parent.mkdir(parents=True, exist_ok=True)
        if new:
            shutil.copy2(new, target)
            if old: updated += 1
            else: added += 1
        elif old:
            shutil.copy2(old, target)
            preserved += 1
    return preserved, added, updated, merged

def _write_layered_report(destination: Path, preserved: int, added: int, updated: int, merged: int, warnings: list[str]) -> None:
    lines = ["Golden Pot layered merge report", f"Mappings preserved from previous version: {preserved}", f"Mappings added from Rainbow: {added}", f"Non-JSON mappings updated from Rainbow: {updated}", f"JSON mapping files semantically merged: {merged}", f"Warnings: {len(warnings)}", "", *(warnings or ["No mapping or texture reference warnings."])]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _mapping_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.json") if is_mapping_path(p.relative_to(root).as_posix())]

def _walk_definitions(value: object):
    if isinstance(value, dict):
        if "bedrock_identifier" in value or "bedrock_options" in value: yield value
        for child in value.values(): yield from _walk_definitions(child)
    elif isinstance(value, list):
        for child in value: yield from _walk_definitions(child)

def _validate_mapping_textures(root: Path, mappings_root: Path | None = None) -> list[str]:
    warnings: list[str] = []
    registry_path = root / "textures" / "item_texture.json"
    texture_data: dict[str, object] = {}
    if registry_path.is_file():
        try:
            registry = read_json(registry_path)
            if isinstance(registry, dict) and isinstance(registry.get("texture_data"), dict): texture_data = registry["texture_data"]
        except (OSError, json.JSONDecodeError): warnings.append("Invalid textures/item_texture.json")
    identifiers: dict[str, str] = {}
    search_root = mappings_root or root
    files = sorted(search_root.rglob("*.json")) if mappings_root is not None else _mapping_files(search_root)
    for mapping_path in files:
        try: mapping = read_json(mapping_path)
        except (OSError, json.JSONDecodeError) as error:
            warnings.append(f"Invalid mapping JSON {mapping_path.relative_to(search_root).as_posix()}: {error}")
            continue
        for definition in _walk_definitions(mapping):
            identifier = definition.get("bedrock_identifier")
            if isinstance(identifier, str):
                if identifier in identifiers: warnings.append(f"Duplicate bedrock_identifier: {identifier}")
                identifiers[identifier] = mapping_path.relative_to(search_root).as_posix()
            options = definition.get("bedrock_options")
            icon = options.get("icon") if isinstance(options, dict) else None
            if not isinstance(icon, str) and isinstance(identifier, str): icon = identifier.replace(":", ".").replace("/", "_")
            if isinstance(icon, str) and icon not in texture_data: warnings.append(f"Mapping icon has no item_texture entry: {icon}")
    for key, entry in texture_data.items():
        values = entry.get("textures") if isinstance(entry, dict) else None
        for texture in values if isinstance(values, list) else [values]:
            if not isinstance(texture, str): continue
            candidate = root / texture.replace("\", "/")
            exists = candidate.is_file() if candidate.suffix else any(candidate.with_suffix(x).is_file() for x in (".png", ".tga", ".jpg", ".jpeg"))
            if not exists: warnings.append(f"Texture path does not exist for {key}: {texture}")
    return warnings

def _write_merge_report(root: Path, merged_json: int, warnings: list[str]) -> None:
    lines = ["Golden Pot semantic merge report", f"Merged mapping/registry JSON files: {merged_json}", f"Warnings: {len(warnings)}", "", *(warnings or ["No mapping or texture reference warnings."])]
    (root / "golden-pot-merge-report.txt").write_text("
".join(lines) + "
", encoding="utf-8")

def _build_pack_zip(root: Path) -> None:
    destination = root / "pack.zip"
    excluded = {"pack.zip", "report.txt", "golden-pot-merge-report.txt"}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.casefold() in excluded: continue
            relative = path.relative_to(root)
            if relative.parts and (relative.parts[0].casefold().startswith("custom_mappings") or relative.parts[0].casefold() == "lang"): continue
            archive.write(path, relative.as_posix())
