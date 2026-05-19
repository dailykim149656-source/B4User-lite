from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from kpeh.core.models import to_plain_data


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row at {path}:{line_number} must be an object")
            rows.append(value)
    return rows


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    ensure_parent_dir(path)
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(to_plain_data(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_yaml_or_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        if source.suffix.lower() == ".json":
            data = json.load(handle)
        else:
            data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


def write_json(path: str | Path, data: Any) -> None:
    ensure_parent_dir(path)
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(to_plain_data(data), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
