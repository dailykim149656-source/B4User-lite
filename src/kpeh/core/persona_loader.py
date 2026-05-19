from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from kpeh.core.io_utils import read_jsonl, read_yaml_or_json
from kpeh.core.models import PersonaRecord, ServiceSpec, ValidationError


def load_personas(path: str | Path) -> list[PersonaRecord]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Persona file not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        rows = read_jsonl(source)
    elif suffix == ".csv":
        rows = _read_csv(source)
    else:
        raise ValueError(f"Unsupported persona file format: {suffix}. Use .jsonl or .csv")

    personas: list[PersonaRecord] = []
    for index, row in enumerate(rows, start=1):
        try:
            personas.append(PersonaRecord.from_dict(row))
        except ValidationError as exc:
            raise ValidationError(f"Invalid persona row {index} in {source}: {exc}") from exc
    return personas


def load_service_spec(path: str | Path) -> ServiceSpec:
    data = read_yaml_or_json(path)
    try:
        return ServiceSpec.from_dict(data)
    except ValidationError as exc:
        raise ValidationError(f"Invalid service spec {path}: {exc}") from exc


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header: {path}")
        rows: list[dict[str, Any]] = []
        for row in reader:
            rows.append({key: _clean_csv_value(value) for key, value in row.items() if key is not None})
        return rows


def _clean_csv_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
