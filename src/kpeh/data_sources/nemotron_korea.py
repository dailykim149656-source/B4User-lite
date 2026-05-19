from __future__ import annotations

import importlib
import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kpeh.core.io_utils import write_json, write_jsonl
from kpeh.core.models import PersonaRecord, ValidationError


DEFAULT_DATASET_ID = "nvidia/Nemotron-Personas-Korea"
DEFAULT_SPLIT = "train"
SOURCE_LICENSE = "cc-by-4.0"

MAPPED_FIELDS = {
    "uuid",
    "persona",
    "age",
    "sex",
    "province",
    "district",
    "occupation",
    "education_level",
}

METADATA_FIELDS = [
    "uuid",
    "professional_persona",
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "family_persona",
    "cultural_background",
    "skills_and_expertise",
    "skills_and_expertise_list",
    "hobbies_and_interests",
    "hobbies_and_interests_list",
    "career_goals_and_ambitions",
    "marital_status",
    "military_status",
    "family_type",
    "housing_type",
    "education_level",
    "bachelors_field",
    "district",
    "country",
]


@dataclass(slots=True)
class ImportSummary:
    dataset: str
    split: str
    source_license: str
    output: str
    summary_output: str
    requested_count: int
    converted_count: int
    source_rows_scanned: int
    seed: int | None
    max_source_rows: int | None
    streaming: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "split": self.split,
            "source_license": self.source_license,
            "output": self.output,
            "summary_output": self.summary_output,
            "requested_count": self.requested_count,
            "converted_count": self.converted_count,
            "source_rows_scanned": self.source_rows_scanned,
            "seed": self.seed,
            "max_source_rows": self.max_source_rows,
            "streaming": self.streaming,
        }


def convert_nemotron_row(
    row: Mapping[str, Any],
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
    source_license: str = SOURCE_LICENSE,
) -> dict[str, Any]:
    """Convert a Nemotron-Personas-Korea row into a PersonaRecord-compatible dict."""

    persona_id = row.get("uuid")
    persona = row.get("persona")
    if persona_id in {None, ""}:
        raise ValidationError("Nemotron row is missing required field: uuid")
    if persona in {None, ""}:
        raise ValidationError("Nemotron row is missing required field: persona")

    source_fields = {
        field: _jsonable(row.get(field))
        for field in METADATA_FIELDS
        if _present(row.get(field))
    }
    converted = {
        "persona_id": str(persona_id),
        "persona": str(persona),
        "age": row.get("age"),
        "gender": row.get("sex") or None,
        "province": row.get("province") or None,
        "city": row.get("district") or None,
        "occupation": row.get("occupation") or None,
        "education": row.get("education_level") or None,
        "metadata": {
            "source_dataset": dataset_id,
            "source_license": source_license,
            "source_fields": source_fields,
        },
    }
    return PersonaRecord.from_dict(converted).to_dict()


def import_nemotron_personas(
    output: str | Path,
    *,
    dataset: str = DEFAULT_DATASET_ID,
    split: str = DEFAULT_SPLIT,
    n: int = 5000,
    seed: int | None = 42,
    max_source_rows: int | None = None,
    streaming: bool = True,
) -> ImportSummary:
    if n <= 0:
        raise ValueError("n must be > 0")
    if max_source_rows is not None and max_source_rows <= 0:
        raise ValueError("max_source_rows must be > 0 when provided")

    rows = _load_dataset_rows(dataset=dataset, split=split, streaming=streaming)
    sampled, scanned = _reservoir_sample_rows(
        rows,
        dataset=dataset,
        n=n,
        seed=seed,
        max_source_rows=max_source_rows,
    )
    if not sampled:
        raise ValueError("No Nemotron personas were converted from the source dataset")

    output_path = Path(output)
    summary_path = _summary_path(output_path)
    write_jsonl(output_path, sampled)
    summary = ImportSummary(
        dataset=dataset,
        split=split,
        source_license=SOURCE_LICENSE,
        output=str(output_path),
        summary_output=str(summary_path),
        requested_count=n,
        converted_count=len(sampled),
        source_rows_scanned=scanned,
        seed=seed,
        max_source_rows=max_source_rows,
        streaming=streaming,
    )
    write_json(summary_path, summary.to_dict())
    return summary


def _load_dataset_rows(dataset: str, split: str, streaming: bool) -> Iterable[Mapping[str, Any]]:
    try:
        datasets_module = importlib.import_module("datasets")
    except ImportError as exc:
        raise RuntimeError(
            "Nemotron import requires optional dependencies. Install with: python -m pip install -e .[hf]"
        ) from exc
    return datasets_module.load_dataset(dataset, split=split, streaming=streaming)


def _reservoir_sample_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    dataset: str,
    n: int,
    seed: int | None,
    max_source_rows: int | None,
) -> tuple[list[dict[str, Any]], int]:
    rng = random.Random(seed)
    sample: list[dict[str, Any]] = []
    converted_seen = 0
    scanned = 0
    for row in rows:
        scanned += 1
        converted = convert_nemotron_row(row, dataset_id=dataset)
        converted_seen += 1
        if len(sample) < n:
            sample.append(converted)
        else:
            replace_index = rng.randint(0, converted_seen - 1)
            if replace_index < n:
                sample[replace_index] = converted
        if max_source_rows is not None and scanned >= max_source_rows:
            break
    return sample, scanned


def _summary_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".summary.json")


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value == "":
        return False
    return True
