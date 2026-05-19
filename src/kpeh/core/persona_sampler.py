from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from kpeh.core.models import PersonaRecord
from kpeh.core.sampling_strategy import SamplingStrategy, load_sampling_strategy


@dataclass(slots=True)
class SampleResult:
    records: list[PersonaRecord]
    warnings: list[str]
    sampling_strategy: SamplingStrategy


def sample_personas(
    personas: list[PersonaRecord],
    n: int,
    filters: dict[str, Any] | None = None,
    seed: int | None = None,
    sampling_strategy: str | SamplingStrategy | dict[str, Any] | None = "random",
) -> SampleResult:
    if n < 0:
        raise ValueError("n must be >= 0")
    strategy = load_sampling_strategy(sampling_strategy)
    filters = filters or {}
    filtered = [persona for persona in personas if _matches_filters(persona, filters)]
    warnings: list[str] = []
    if len(filtered) < n:
        warnings.append(f"Requested {n} personas but only {len(filtered)} matched filters")
        n = len(filtered)
    if n == 0:
        return SampleResult(records=[], warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "first":
        return SampleResult(records=filtered[:n], warnings=warnings, sampling_strategy=strategy)
    rng = random.Random(seed)
    if strategy.strategy == "random":
        return SampleResult(records=rng.sample(filtered, n), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "balanced_by_age":
        return SampleResult(records=_balanced_sample(filtered, n, rng, _age_bucket), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "balanced_by_region":
        return SampleResult(records=_balanced_sample(filtered, n, rng, _region_bucket), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "balanced_by_occupation":
        return SampleResult(records=_balanced_sample(filtered, n, rng, _occupation_bucket), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "digital_literacy_stratified":
        return SampleResult(records=_balanced_sample(filtered, n, rng, _digital_bucket), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "edge_case_sampling":
        return SampleResult(records=_edge_case_sample(filtered, n, rng), warnings=warnings, sampling_strategy=strategy)
    if strategy.strategy == "target_segment_oversampling":
        records, segment_warnings = _target_segment_oversample(filtered, n, rng, strategy)
        return SampleResult(records=records, warnings=warnings + segment_warnings, sampling_strategy=strategy)
    if strategy.strategy == "panel":
        from kpeh.core.panel_builder import build_panel_records

        records, _manifest, panel_warnings = build_panel_records(
            personas=filtered,
            strategy=strategy,
            n_personas=n,
            seed=seed,
        )
        return SampleResult(records=records, warnings=warnings + panel_warnings, sampling_strategy=strategy)
    raise ValueError(f"Unsupported sampling_strategy: {strategy.strategy}")


def _matches_filters(persona: PersonaRecord, filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if expected is None or expected == "":
            continue
        if key == "age_min":
            if persona.age is None or persona.age < int(expected):
                return False
            continue
        if key == "age_max":
            if persona.age is None or persona.age > int(expected):
                return False
            continue
        if key.endswith("_contains"):
            field_name = key[: -len("_contains")]
            actual = _get_value(persona, field_name)
            expected_values = expected if isinstance(expected, (list, tuple, set)) else [expected]
            if not any(str(item).lower() in str(actual or "").lower() for item in expected_values):
                return False
            continue
        actual = _get_value(persona, key)
        if isinstance(expected, (list, tuple, set)):
            if str(actual or "") not in {str(item) for item in expected}:
                return False
        elif str(actual or "") != str(expected):
            return False
    return True


def _get_value(persona: PersonaRecord, key: str) -> Any:
    if hasattr(persona, key):
        return getattr(persona, key)
    if key in persona.metadata:
        return persona.metadata.get(key)
    source_fields = persona.metadata.get("source_fields")
    if isinstance(source_fields, dict):
        return source_fields.get(key)
    return None


def _balanced_sample(
    personas: list[PersonaRecord],
    n: int,
    rng: random.Random,
    bucket_fn: Any,
) -> list[PersonaRecord]:
    buckets: dict[str, list[PersonaRecord]] = {}
    for persona in personas:
        buckets.setdefault(str(bucket_fn(persona)), []).append(persona)
    for records in buckets.values():
        rng.shuffle(records)
    bucket_names = sorted(buckets)
    selected: list[PersonaRecord] = []
    while len(selected) < n and any(buckets.values()):
        for bucket in bucket_names:
            if buckets[bucket] and len(selected) < n:
                selected.append(buckets[bucket].pop(0))
    return selected


def _target_segment_oversample(
    personas: list[PersonaRecord],
    n: int,
    rng: random.Random,
    strategy: SamplingStrategy,
) -> tuple[list[PersonaRecord], list[str]]:
    warnings: list[str] = []
    selected: list[PersonaRecord] = []
    selected_ids: set[str] = set()
    for segment in strategy.target_segments:
        allocation = int(n * segment.weight)
        if allocation <= 0:
            continue
        candidates = [
            persona
            for persona in personas
            if persona.persona_id not in selected_ids and _matches_filters(persona, segment.conditions)
        ]
        rng.shuffle(candidates)
        chosen = candidates[:allocation]
        if len(chosen) < allocation:
            warnings.append(
                f"Target segment {segment.name} requested {allocation} personas but only {len(chosen)} matched"
            )
        selected.extend(chosen)
        selected_ids.update(persona.persona_id for persona in chosen)

    remaining = [persona for persona in personas if persona.persona_id not in selected_ids]
    needed = n - len(selected)
    if needed > 0:
        rng.shuffle(remaining)
        selected.extend(remaining[:needed])
    return selected[:n], warnings


def _edge_case_sample(personas: list[PersonaRecord], n: int, rng: random.Random) -> list[PersonaRecord]:
    scored = [(persona, _edge_case_score(persona), rng.random()) for persona in personas]
    scored.sort(key=lambda item: (-item[1], item[2]))
    return [persona for persona, _score, _tie_breaker in scored[:n]]


def _edge_case_score(persona: PersonaRecord) -> int:
    score = 0
    if persona.age is not None and persona.age >= 60:
        score += 3
    if (persona.digital_literacy or "").lower() in {"low", "medium_low", "낮음"}:
        score += 3
    if (persona.technology_attitude or "").lower() in {"cautious", "skeptical", "보수적"}:
        score += 2
    for key in ["occupation", "province", "city", "digital_literacy", "technology_attitude"]:
        if not _get_value(persona, key):
            score += 1
    return score


def _age_bucket(persona: PersonaRecord) -> str:
    if persona.age is None:
        return "unknown"
    if persona.age < 30:
        return "under_30"
    if persona.age < 50:
        return "30_49"
    return "50_plus"


def _region_bucket(persona: PersonaRecord) -> str:
    return str(persona.province or "unknown")


def _occupation_bucket(persona: PersonaRecord) -> str:
    return str(persona.occupation or persona.industry or "unknown")


def _digital_bucket(persona: PersonaRecord) -> str:
    return str(persona.digital_literacy or "unknown")
