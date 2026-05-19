from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kpeh.core.io_utils import read_yaml_or_json


SUPPORTED_SAMPLING_STRATEGIES = {
    "random",
    "first",
    "balanced_by_age",
    "balanced_by_region",
    "balanced_by_occupation",
    "digital_literacy_stratified",
    "edge_case_sampling",
    "target_segment_oversampling",
    "panel",
}


@dataclass(slots=True)
class TargetSegment:
    name: str
    weight: float
    conditions: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetSegment":
        name = data.get("name")
        conditions = data.get("conditions")
        if not name:
            raise ValueError("target_segments entries require name")
        if "weight" not in data:
            raise ValueError(f"target segment {name} requires weight")
        if not isinstance(conditions, dict) or not conditions:
            raise ValueError(f"target segment {name} requires non-empty conditions")
        weight = float(data["weight"])
        if weight < 0:
            raise ValueError(f"target segment {name} weight must be >= 0")
        return cls(name=str(name), weight=weight, conditions=dict(conditions))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight, "conditions": dict(self.conditions)}


@dataclass(slots=True)
class SamplingStrategy:
    strategy: str = "random"
    target_segments: list[TargetSegment] = field(default_factory=list)
    source: str | None = None
    version: int = 1
    name: str | None = None
    description: str | None = None
    dataset: dict[str, Any] = field(default_factory=dict)
    panel: dict[str, Any] = field(default_factory=dict)
    candidate_filters: dict[str, Any] = field(default_factory=dict)
    segment_rules: dict[str, Any] = field(default_factory=dict)
    quota: dict[str, float | int] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    diversity_limits: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, float] = field(default_factory=dict)
    backfill: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source: str | None = None) -> "SamplingStrategy":
        raw = dict(data)
        strategy = str(data.get("strategy") or ("panel" if _looks_like_panel_strategy(data) else "random"))
        if strategy not in SUPPORTED_SAMPLING_STRATEGIES:
            raise ValueError(f"Unsupported sampling_strategy: {strategy}")
        segments = [TargetSegment.from_dict(item) for item in _as_list(data.get("target_segments"))]
        if strategy == "target_segment_oversampling" and not segments:
            segments = _default_target_segments()
        total_weight = sum(segment.weight for segment in segments)
        if total_weight > 1.0:
            raise ValueError("target segment weights must sum to <= 1.0")
        quota = _number_map(data.get("quota"), "quota")
        _validate_coverage(data.get("coverage"))
        return cls(
            strategy=strategy,
            target_segments=segments,
            source=source,
            version=int(data.get("version") or (2 if strategy == "panel" else 1)),
            name=str(data.get("name")) if data.get("name") else None,
            description=str(data.get("description")) if data.get("description") else None,
            dataset=dict(data.get("dataset") or {}),
            panel=dict(data.get("panel") or {}),
            candidate_filters=dict(data.get("candidate_filters") or {}),
            segment_rules=dict(data.get("segment_rules") or {}),
            quota=quota,
            coverage=dict(data.get("coverage") or {}),
            diversity_limits=dict(data.get("diversity_limits") or {}),
            scoring={key: float(value) for key, value in _number_map(data.get("scoring"), "scoring").items()},
            backfill=dict(data.get("backfill") or {}),
            outputs=dict(data.get("outputs") or {}),
            raw=raw,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "strategy": self.strategy,
            "source": self.source,
            "target_segments": [segment.to_dict() for segment in self.target_segments],
        }
        if self.strategy == "panel" or self.version > 1:
            data.update(
                {
                    "version": self.version,
                    "name": self.name,
                    "description": self.description,
                    "dataset": dict(self.dataset),
                    "panel": dict(self.panel),
                    "candidate_filters": dict(self.candidate_filters),
                    "segment_rules": dict(self.segment_rules),
                    "quota": dict(self.quota),
                    "coverage": dict(self.coverage),
                    "diversity_limits": dict(self.diversity_limits),
                    "scoring": dict(self.scoring),
                    "backfill": dict(self.backfill),
                    "outputs": dict(self.outputs),
                }
            )
        return {key: value for key, value in data.items() if value not in (None, {}, [])}


def load_sampling_strategy(source: str | Path | dict[str, Any] | SamplingStrategy | None = None) -> SamplingStrategy:
    if isinstance(source, SamplingStrategy):
        return source
    if source is None or source == "":
        return SamplingStrategy()
    if isinstance(source, dict):
        return SamplingStrategy.from_dict(source)
    path = Path(str(source))
    if path.exists():
        return SamplingStrategy.from_dict(read_yaml_or_json(path), source=str(path))
    return SamplingStrategy.from_dict({"strategy": str(source)}, source=str(source))


def _default_target_segments() -> list[TargetSegment]:
    return [
        TargetSegment(
            name="small_business_owner",
            weight=0.4,
            conditions={"occupation_contains": ["자영업", "소상공인", "사업자"]},
        ),
        TargetSegment(
            name="low_digital_literacy",
            weight=0.3,
            conditions={"digital_literacy": ["low", "낮음"]},
        ),
    ]


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _looks_like_panel_strategy(data: dict[str, Any]) -> bool:
    return any(key in data for key in ["candidate_filters", "segment_rules", "quota", "coverage", "diversity_limits"])


def _number_map(value: Any, label: str) -> dict[str, float | int]:
    if value is None or value == "":
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    result: dict[str, float | int] = {}
    for key, raw in value.items():
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}.{key} must be numeric") from exc
        if number < 0:
            raise ValueError(f"{label}.{key} must be >= 0")
        result[str(key)] = int(number) if number.is_integer() else number
    return result


def _validate_coverage(value: Any) -> None:
    if value is None or value == "":
        return
    if not isinstance(value, dict):
        raise ValueError("coverage must be an object")
    for group, rules in value.items():
        if not isinstance(rules, dict):
            raise ValueError(f"coverage.{group} must be an object")
        for bucket, limits in rules.items():
            if not isinstance(limits, dict):
                raise ValueError(f"coverage.{group}.{bucket} must be an object")
            minimum = limits.get("min")
            maximum = limits.get("max")
            for label, raw in [("min", minimum), ("max", maximum)]:
                if raw is None:
                    continue
                try:
                    number = float(raw)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"coverage.{group}.{bucket}.{label} must be numeric") from exc
                if number < 0:
                    raise ValueError(f"coverage.{group}.{bucket}.{label} must be >= 0")
            if minimum is not None and maximum is not None and float(minimum) > float(maximum):
                raise ValueError(f"coverage.{group}.{bucket}.min must be <= max")
