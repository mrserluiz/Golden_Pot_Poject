from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any


def _identity(value: Any) -> tuple[Any, ...] | None:
    if not isinstance(value, dict):
        return None
    for keys in (
        ("bedrock_identifier",),
        ("identifier",),
        ("name",),
        ("id",),
        ("model", "custom_model_data"),
        ("model", "type"),
    ):
        if all(key in value for key in keys):
            return keys + tuple(json.dumps(value[key], sort_keys=True) for key in keys)
    return None


def merge_values(previous: Any, current: Any) -> Any:
    """Merge JSON-compatible values while giving current values precedence."""
    if isinstance(previous, dict) and isinstance(current, dict):
        result = copy.deepcopy(previous)
        for key, value in current.items():
            result[key] = merge_values(result[key], value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(previous, list) and isinstance(current, list):
        result = copy.deepcopy(previous)
        positions = {
            identity: index
            for index, item in enumerate(result)
            if (identity := _identity(item)) is not None
        }
        serialized = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in result}
        for item in current:
            identity = _identity(item)
            if identity is not None and identity in positions:
                index = positions[identity]
                result[index] = merge_values(result[index], item)
            else:
                encoded = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if encoded not in serialized:
                    positions[identity] = len(result) if identity is not None else -1
                    result.append(copy.deepcopy(item))
                    serialized.add(encoded)
        return result
    return copy.deepcopy(current)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def is_mapping_path(relative_path: str) -> bool:
    parts = relative_path.casefold().split("/")
    return relative_path.casefold().endswith(".json") and any(
        part.startswith("custom_mappings") for part in parts
    )


def is_pack_registry(relative_path: str) -> bool:
    normalized = relative_path.casefold()
    return normalized in {
        "textures/item_texture.json",
        "textures/terrain_texture.json",
        "textures/flipbook_textures.json",
        "sounds/sound_definitions.json",
        "sound_definitions.json",
    }


def merge_json_files(previous: Path, current: Path, destination: Path) -> None:
    write_json(destination, merge_values(read_json(previous), read_json(current)))


def _version(value: Any) -> list[int]:
    if isinstance(value, list) and len(value) == 3 and all(isinstance(part, int) for part in value):
        return list(value)
    return [1, 0, 0]


def update_manifest(previous: Path | None, current: Path | None, destination: Path) -> None:
    """Keep the previous pack identity and publish a new patch-level version."""
    source = previous if previous and previous.is_file() else current
    data = read_json(source) if source else {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("format_version", 2)
    header = data.setdefault("header", {})
    if not isinstance(header, dict):
        header = data["header"] = {}
    header.setdefault("name", "Golden Pot merged resource pack")
    header.setdefault("description", "Merged by Golden Pot")
    header.setdefault("uuid", str(uuid.uuid4()))
    version = _version(header.get("version"))
    version[2] += 1
    header["version"] = version
    header.setdefault("min_engine_version", [1, 20, 0])

    modules = data.setdefault("modules", [])
    if not isinstance(modules, list) or not modules:
        modules = data["modules"] = [{
            "type": "resources", "uuid": str(uuid.uuid4()), "version": version
        }]
    for module in modules:
        if isinstance(module, dict):
            module.setdefault("type", "resources")
            module.setdefault("uuid", str(uuid.uuid4()))
            module["version"] = version
    write_json(destination, data)
