from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from kpeh.core.io_utils import read_yaml_or_json
from kpeh.core.models import EvaluationRubric


def load_rubric(source: str | Path | None = None) -> EvaluationRubric:
    data = _load_domain_or_file(source, "rubrics.yaml")
    return EvaluationRubric.from_dict(data)


def load_market_fit_rubric(source: str | Path | None = None) -> EvaluationRubric:
    data = _load_domain_or_file(source, "market_fit_rubrics.yaml")
    return EvaluationRubric.from_dict(data)


def load_failure_modes(source: str | Path | None = None) -> dict[str, dict[str, Any]]:
    data = _load_domain_or_file(source, "failure_modes.yaml")
    modes = data.get("failure_modes")
    if not isinstance(modes, dict):
        raise ValueError("failure_modes.yaml must contain a failure_modes object")
    return {str(code): dict(value or {}) for code, value in modes.items()}


def load_roles(source: str | Path | None = None) -> dict[str, Any]:
    try:
        data = _load_domain_or_file(source, "roles.yaml")
    except FileNotFoundError:
        data = _load_packaged_resource("generic", "roles.yaml")
    roles = data.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("roles.yaml must contain a roles object")
    segment_labels = data.get("segment_labels") or {}
    if not isinstance(segment_labels, dict):
        raise ValueError("roles.yaml segment_labels must be an object")
    return {
        "roles": {str(code): dict(value or {}) for code, value in roles.items()},
        "segment_labels": {str(code): str(value) for code, value in segment_labels.items()},
    }


def _load_domain_or_file(source: str | Path | None, filename: str) -> dict[str, Any]:
    if source is None or str(source) == "generic":
        return _load_packaged_resource("generic", filename)

    path = Path(source)
    if path.is_dir():
        return read_yaml_or_json(path / filename)
    if path.is_file():
        return read_yaml_or_json(path)
    return _load_packaged_resource(str(source), filename)


def _load_packaged_resource(domain_pack: str, filename: str) -> dict[str, Any]:
    resource = resources.files("kpeh").joinpath("domain_packs", domain_pack, filename)
    if not resource.is_file():
        raise FileNotFoundError(f"Packaged domain pack file not found: {domain_pack}/{filename}")
    with resource.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid packaged resource: {domain_pack}/{filename}")
    return data
