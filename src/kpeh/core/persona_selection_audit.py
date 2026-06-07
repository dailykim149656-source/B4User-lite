from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from kpeh.core.io_utils import ensure_parent_dir, write_json
from kpeh.core.models import AgentConcept, PersonaProfile, ServiceSpec
from kpeh.core.sampling_strategy import SamplingStrategy, load_sampling_strategy


SYNTHETIC_SELECTION_NOTICE = (
    "This persona selection audit explains a synthetic panel. It is a targeting "
    "and coverage hypothesis, not proof of real user demand or market fit."
)


def build_persona_selection_audit(
    *,
    profiles: list[PersonaProfile],
    sampling_strategy: str | Path | dict[str, Any] | SamplingStrategy | None,
    requested_n: int | None = None,
    seed: int | None = None,
    filters: dict[str, Any] | None = None,
    target: ServiceSpec | AgentConcept | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    strategy = load_sampling_strategy(sampling_strategy)
    profile_rows = [_profile_row(profile, target) for profile in profiles]
    selected_count = len(profiles)
    unique_personas = {profile.persona_id for profile in profiles}
    sampling_scores = [
        float(row["sampling_score"])
        for row in profile_rows
        if isinstance(row.get("sampling_score"), (int, float))
    ]
    keyword_scores = [
        float(row["target_keyword_score"])
        for row in profile_rows
        if isinstance(row.get("target_keyword_score"), (int, float))
    ]
    target_definition = _target_definition(target, strategy)
    coverage = _coverage(profile_rows)
    data_quality = _data_quality(profile_rows)
    target_fit = _target_fit(profile_rows, strategy, target, sampling_scores, keyword_scores)
    validation_decision = _validation_decision(
        strategy=strategy,
        requested_n=requested_n,
        selected_count=selected_count,
        target_definition=target_definition,
        data_quality=data_quality,
        target_fit=target_fit,
        sampling_scores=sampling_scores,
    )
    audit_warnings = list(warnings or [])
    audit_warnings.extend(
        _audit_warnings(
            profiles=profiles,
            strategy=strategy,
            requested_n=requested_n,
            selected_count=selected_count,
            data_quality=data_quality,
            target_fit=target_fit,
            sampling_scores=sampling_scores,
            validation_decision=validation_decision,
        )
    )
    review_rows = _review_rows(profile_rows)
    return {
        "notice": SYNTHETIC_SELECTION_NOTICE,
        "summary": {
            "requested_count": requested_n,
            "selected_count": selected_count,
            "unique_persona_count": len(unique_personas),
            "duplicate_persona_count": selected_count - len(unique_personas),
            "seed": seed,
            "filters": filters or {},
        },
        "sampling_strategy": strategy.to_dict(),
        "selection_logic": _selection_logic(strategy),
        "target_definition": target_definition,
        "coverage": coverage,
        "target_fit": target_fit,
        "validation_decision": validation_decision,
        "data_quality": data_quality,
        "human_review_queue": review_rows,
        "human_review_checklist": _human_review_checklist(validation_decision),
        "warnings": _dedupe(audit_warnings),
    }


def write_persona_selection_audit(path: str | Path, audit: dict[str, Any]) -> None:
    write_json(path, audit)


def write_persona_selection_report(path: str | Path, audit: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    Path(path).write_text("\n".join(markdown_lines_from_audit(audit)), encoding="utf-8", newline="\n")


def markdown_lines_from_audit(audit: dict[str, Any], *, heading_level: int = 2, review_limit: int = 5) -> list[str]:
    prefix = "#" * heading_level
    summary = dict(audit.get("summary") or {})
    strategy = dict(audit.get("sampling_strategy") or {})
    target_definition = dict(audit.get("target_definition") or {})
    target_fit = dict(audit.get("target_fit") or {})
    validation_decision = dict(audit.get("validation_decision") or {})
    data_quality = dict(audit.get("data_quality") or {})
    coverage = dict(audit.get("coverage") or {})
    lines = [
        f"{prefix} Persona Selection Audit",
        "",
        f"> {audit.get('notice') or SYNTHETIC_SELECTION_NOTICE}",
        "",
        "- strategy: {strategy}".format(strategy=strategy.get("strategy") or "unknown"),
        "- strategy_source: {source}".format(source=strategy.get("source") or "inline/default"),
        "- requested_count: {requested}".format(requested=summary.get("requested_count")),
        "- selected_count: {selected}".format(selected=summary.get("selected_count", 0)),
        "- seed: {seed}".format(seed=summary.get("seed")),
        "- target_fit_status: {status}".format(status=target_fit.get("status", "needs_review")),
        "- target_fit_basis: {basis}".format(basis=target_fit.get("basis", "not_available")),
        "- validation_decision: {decision}".format(
            decision=validation_decision.get("status", "human_review_required")
        ),
        "",
        f"{prefix}# Selection Logic",
        "",
    ]
    for item in audit.get("selection_logic") or []:
        lines.append(f"- {item}")
    lines.extend(["", f"{prefix}# Target Definition", ""])
    lines.append("- target_type: {target_type}".format(target_type=target_definition.get("target_type", "not_provided")))
    if target_definition.get("name"):
        lines.append("- target_name: {name}".format(name=target_definition.get("name")))
    for key in ["target_users", "capabilities", "known_limits", "prohibited_claims"]:
        values = [str(item) for item in list(target_definition.get(key) or [])[:6]]
        if values:
            lines.append("- {key}: {values}".format(key=key, values="; ".join(values)))
    lines.extend(["", f"{prefix}# Validation Decision", ""])
    lines.append("- status: {status}".format(status=validation_decision.get("status", "human_review_required")))
    lines.append("- confidence: {confidence}".format(confidence=validation_decision.get("confidence", "low")))
    for item in validation_decision.get("rationale") or []:
        lines.append(f"- rationale: {item}")
    for item in validation_decision.get("blocking_issues") or []:
        lines.append(f"- blocking_issue: {item}")
    for item in validation_decision.get("review_issues") or []:
        lines.append(f"- review_issue: {item}")
    for item in list(validation_decision.get("recommended_next_actions") or [])[:5]:
        lines.append(f"- next_action: {item}")
    lines.extend(["", f"{prefix}# Coverage Snapshot", ""])
    for section in ["segment", "quota_bucket", "age_band", "digital_literacy", "region", "occupation_top"]:
        values = dict(coverage.get(section) or {})
        if not values:
            continue
        inline = ", ".join(f"{key}: {value}" for key, value in list(values.items())[:8])
        lines.append(f"- {section}: {inline}")
    lines.extend(["", f"{prefix}# Data Quality Flags", ""])
    for key in [
        "missing_age_count",
        "missing_occupation_count",
        "missing_region_count",
        "missing_persona_text_count",
        "generic_segment_count",
        "low_sampling_score_count",
    ]:
        lines.append(f"- {key}: {data_quality.get(key, 0)}")
    warnings = list(audit.get("warnings") or [])
    if warnings:
        lines.extend(["", f"{prefix}# Warnings", ""])
        for warning in warnings[:8]:
            lines.append(f"- {warning}")
    review_rows = list(audit.get("human_review_queue") or [])[:review_limit]
    if review_rows:
        lines.extend(["", f"{prefix}# Human Review Candidates", ""])
        for row in review_rows:
            reasons = ", ".join(str(item) for item in row.get("reasons", []))
            lines.append(
                "- {persona_id} / {segment}: {reasons}".format(
                    persona_id=row.get("persona_id"),
                    segment=row.get("segment"),
                    reasons=reasons or "manual_review",
                )
            )
    checklist = list(audit.get("human_review_checklist") or [])
    if checklist:
        lines.extend(["", f"{prefix}# Human Review Checklist", ""])
        for item in checklist[:8]:
            lines.append(f"- {item}")
    lines.append("")
    return lines


def _profile_row(profile: PersonaProfile, target: ServiceSpec | AgentConcept | None) -> dict[str, Any]:
    metadata = dict(profile.metadata or {})
    source_fields = dict(metadata.get("source_fields") or {})
    panel = dict(metadata.get("panel_metadata") or {})
    scores = dict(metadata.get("sampling_scores") or {})
    return {
        "profile_id": profile.profile_id,
        "persona_id": profile.persona_id,
        "segment": profile.segment,
        "summary": profile.summary,
        "source_fields": source_fields,
        "panel_metadata": panel,
        "sampling_score": _optional_float(scores.get("domain_relevance_score")),
        "target_keyword_score": _target_keyword_score(profile, target),
    }


def _coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "segment": _count(row.get("segment") for row in rows),
        "quota_bucket": _count(
            dict(row.get("panel_metadata") or {}).get("quota_bucket") or "unknown"
            for row in rows
        ),
        "age_band": _count(_age_band(dict(row.get("source_fields") or {}).get("age")) for row in rows),
        "digital_literacy": _count(
            str(dict(row.get("source_fields") or {}).get("digital_literacy") or "unknown")
            for row in rows
        ),
        "region": _count(
            str(dict(row.get("source_fields") or {}).get("province") or "unknown")
            for row in rows
        ),
        "occupation_top": dict(
            Counter(
                str(
                    dict(row.get("source_fields") or {}).get("occupation")
                    or dict(row.get("source_fields") or {}).get("industry")
                    or "unknown"
                )
                for row in rows
            ).most_common(10)
        ),
    }


def _data_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_age = 0
    missing_occupation = 0
    missing_region = 0
    missing_persona_text = 0
    generic_segment = 0
    low_sampling_score = 0
    for row in rows:
        source = dict(row.get("source_fields") or {})
        if source.get("age") in (None, ""):
            missing_age += 1
        if not (source.get("occupation") or source.get("industry")):
            missing_occupation += 1
        if not (source.get("province") or source.get("city")):
            missing_region += 1
        if not str(source.get("persona") or "").strip():
            missing_persona_text += 1
        if "general_user" in str(row.get("segment") or ""):
            generic_segment += 1
        score = row.get("sampling_score")
        if isinstance(score, (int, float)) and score < 0.2:
            low_sampling_score += 1
    return {
        "missing_age_count": missing_age,
        "missing_occupation_count": missing_occupation,
        "missing_region_count": missing_region,
        "missing_persona_text_count": missing_persona_text,
        "generic_segment_count": generic_segment,
        "low_sampling_score_count": low_sampling_score,
    }


def _target_fit(
    rows: list[dict[str, Any]],
    strategy: SamplingStrategy,
    target: ServiceSpec | AgentConcept | None,
    sampling_scores: list[float],
    keyword_scores: list[float],
) -> dict[str, Any]:
    if sampling_scores:
        average = round(sum(sampling_scores) / len(sampling_scores), 4)
        low_count = sum(1 for score in sampling_scores if score < 0.2)
        return {
            "status": _status_from_score(average, low_count, len(rows)),
            "basis": "panel_domain_relevance_score",
            "average_score": average,
            "low_score_count": low_count,
            "scored_count": len(sampling_scores),
        }
    if target and keyword_scores:
        average = round(sum(keyword_scores) / len(keyword_scores), 4)
        low_count = sum(1 for score in keyword_scores if score < 0.1)
        return {
            "status": _status_from_score(average, low_count, len(rows)),
            "basis": "target_keyword_overlap",
            "average_score": average,
            "low_score_count": low_count,
            "scored_count": len(keyword_scores),
        }
    if strategy.strategy in {"random", "first"}:
        return {
            "status": "needs_review",
            "basis": "strategy_has_no_target_fit_signal",
            "average_score": None,
            "low_score_count": None,
            "scored_count": 0,
        }
    return {
        "status": "partial",
        "basis": "strategy_metadata_only",
        "average_score": None,
        "low_score_count": None,
        "scored_count": 0,
    }


def _target_definition(target: ServiceSpec | AgentConcept | None, strategy: SamplingStrategy) -> dict[str, Any]:
    if isinstance(target, ServiceSpec):
        target_type = "service_spec"
        target_id = target.service_id
        capabilities = list(target.service_capabilities)
    elif isinstance(target, AgentConcept):
        target_type = "agent_concept"
        target_id = target.concept_id
        capabilities = list(target.capabilities)
    else:
        target_type = "not_provided"
        target_id = None
        capabilities = []
    target_users = list(target.target_users) if target else []
    known_limits = list(target.known_limits) if target else []
    prohibited_claims = list(target.prohibited_claims) if target else []
    return {
        "target_type": target_type,
        "target_id": target_id,
        "name": target.name if target else None,
        "target_users": target_users,
        "capabilities": capabilities,
        "known_limits": known_limits,
        "prohibited_claims": prohibited_claims,
        "sampling_constraints": {
            "candidate_filters": dict(strategy.candidate_filters),
            "target_segments": [segment.to_dict() for segment in strategy.target_segments],
            "quota": dict(strategy.quota),
            "coverage": dict(strategy.coverage),
        },
    }


def _validation_decision(
    *,
    strategy: SamplingStrategy,
    requested_n: int | None,
    selected_count: int,
    target_definition: dict[str, Any],
    data_quality: dict[str, Any],
    target_fit: dict[str, Any],
    sampling_scores: list[float],
) -> dict[str, Any]:
    blocking_issues: list[str] = []
    review_issues: list[str] = []
    rationale: list[str] = []
    recommended_next_actions: list[str] = []

    if selected_count == 0:
        blocking_issues.append("no_selected_personas")
        recommended_next_actions.append("Relax filters or fix the persona dataset before generating a report.")
    elif selected_count < 3:
        review_issues.append("very_small_panel")
        recommended_next_actions.append("Increase n_personas before interpreting segment-level patterns.")

    if requested_n is not None and selected_count < requested_n:
        review_issues.append("selected_count_below_request")
        recommended_next_actions.append("Review filters and candidate pool size before rerunning.")

    if target_definition.get("target_type") == "not_provided":
        review_issues.append("target_not_provided")
        recommended_next_actions.append("Provide a service or concept config with explicit target_users.")
    elif not target_definition.get("target_users"):
        review_issues.append("target_users_not_declared")
        recommended_next_actions.append("Declare target_users before using target-fit language.")

    if strategy.strategy in {"random", "first"}:
        review_issues.append("sampling_strategy_has_no_target_validation")
        recommended_next_actions.append("Use a panel or target-segment sampling strategy for target-user validation.")

    if strategy.strategy == "panel" and not sampling_scores:
        review_issues.append("panel_rows_missing_domain_relevance_score")
        recommended_next_actions.append("Rebuild the panel so each selected row carries domain_relevance_score metadata.")

    fit_status = str(target_fit.get("status") or "needs_review")
    if fit_status == "needs_review":
        blocking_issues.append("target_fit_needs_review")
        recommended_next_actions.append("Manually inspect low-fit or unscored personas before using this run as evidence.")
    elif fit_status == "partial":
        review_issues.append("target_fit_partial")
        recommended_next_actions.append("Treat findings as weak exploratory signals until panel relevance is improved.")
    else:
        rationale.append("target_fit_signal_is_present")

    if data_quality.get("generic_segment_count", 0) > max(0, selected_count // 2):
        review_issues.append("generic_segment_overrepresented")
        recommended_next_actions.append("Tighten segment rules or remove generic personas from the selected panel.")
    if data_quality.get("missing_occupation_count", 0) > max(0, selected_count // 3):
        review_issues.append("occupation_or_industry_missing_for_many_personas")
        recommended_next_actions.append("Enrich occupation or industry fields before industry-specific conclusions.")

    if blocking_issues:
        status = "insufficient_for_target_claims"
        confidence = "low"
    elif review_issues:
        status = "human_review_required"
        confidence = "low"
    else:
        status = "usable_for_synthetic_exploration"
        confidence = "medium"
        rationale.append("no_blocking_panel_quality_flags")

    return {
        "status": status,
        "confidence": confidence,
        "rationale": _dedupe(rationale),
        "blocking_issues": _dedupe(blocking_issues),
        "review_issues": _dedupe(review_issues),
        "recommended_next_actions": _dedupe(recommended_next_actions),
    }


def _human_review_checklist(validation_decision: dict[str, Any]) -> list[str]:
    checklist = [
        "Confirm that target_users match the service or concept being evaluated.",
        "Review human_review_queue rows before using segment-level conclusions.",
        "Check whether target_fit_basis is panel_domain_relevance_score or only a weaker fallback.",
        "Remove, enrich, or downweight generic personas and rows with missing occupation or industry.",
        "Keep report language framed as synthetic product-discovery hypotheses.",
    ]
    if validation_decision.get("status") == "insufficient_for_target_claims":
        checklist.insert(0, "Do not use this run for target-user claims until blocking issues are resolved.")
    return checklist


def _selection_logic(strategy: SamplingStrategy) -> list[str]:
    if strategy.strategy == "panel":
        return [
            "Filter the persona dataset with candidate_filters.",
            "Assign segment tags with segment_rules.",
            "Score candidates with weighted relevance components.",
            "Allocate rows with quota and diversity limits.",
            "Backfill only when target buckets do not have enough eligible personas.",
        ]
    if strategy.strategy == "target_segment_oversampling":
        items = ["Oversample named target segments before filling the remaining rows."]
        for segment in strategy.target_segments:
            items.append(
                "Target segment {name}: weight={weight}, conditions={conditions}".format(
                    name=segment.name,
                    weight=segment.weight,
                    conditions=segment.conditions,
                )
            )
        return items
    if strategy.strategy.startswith("balanced_by_"):
        return [f"Round-robin sample across {strategy.strategy.removeprefix('balanced_by_')} buckets."]
    if strategy.strategy == "digital_literacy_stratified":
        return ["Round-robin sample across digital_literacy buckets."]
    if strategy.strategy == "edge_case_sampling":
        return ["Rank personas by edge-case risk proxies such as older age, low digital literacy, and missing fields."]
    if strategy.strategy == "first":
        return ["Use the first eligible personas after filters. This is deterministic but not target validated."]
    return ["Random sample from eligible personas after filters. This is reproducible with seed but not target validated."]


def _audit_warnings(
    *,
    profiles: list[PersonaProfile],
    strategy: SamplingStrategy,
    requested_n: int | None,
    selected_count: int,
    data_quality: dict[str, Any],
    target_fit: dict[str, Any],
    sampling_scores: list[float],
    validation_decision: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if requested_n is not None and selected_count < requested_n:
        warnings.append(f"Only {selected_count} personas were selected from requested {requested_n}.")
    if not profiles:
        warnings.append("No personas were selected; reports cannot support target-fit claims.")
    if strategy.strategy in {"random", "first"}:
        warnings.append("Sampling strategy does not validate target fit; use a panel strategy for launch-readiness claims.")
    if not sampling_scores and strategy.strategy == "panel":
        warnings.append("Panel strategy was used but profile rows do not contain domain_relevance_score metadata.")
    if target_fit.get("status") == "needs_review":
        warnings.append("Target user fit needs human review before using this run as evidence.")
    if data_quality.get("generic_segment_count", 0) > max(0, selected_count // 2):
        warnings.append("More than half of selected personas are generic segments; tighten filters or segment rules.")
    if data_quality.get("missing_occupation_count", 0) > 0:
        warnings.append("Some selected personas lack occupation or industry fields.")
    if validation_decision.get("status") == "insufficient_for_target_claims":
        warnings.append("Persona panel is insufficient for target-user claims without human review and rerun.")
    return warnings


def _review_rows(rows: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        reasons: list[str] = []
        source = dict(row.get("source_fields") or {})
        score = row.get("sampling_score")
        if score is None:
            reasons.append("missing_sampling_score")
        elif isinstance(score, (int, float)) and score < 0.2:
            reasons.append("low_sampling_score")
        if not (source.get("occupation") or source.get("industry")):
            reasons.append("missing_occupation")
        if not source.get("persona"):
            reasons.append("missing_persona_text")
        if "general_user" in str(row.get("segment") or ""):
            reasons.append("generic_segment")
        if not reasons:
            continue
        candidates.append(
            (
                len(reasons),
                {
                    "profile_id": row.get("profile_id"),
                    "persona_id": row.get("persona_id"),
                    "segment": row.get("segment"),
                    "sampling_score": score,
                    "summary": row.get("summary"),
                    "reasons": reasons,
                },
            )
        )
    candidates.sort(key=lambda item: (-item[0], str(item[1].get("persona_id"))))
    return [row for _score, row in candidates[:limit]]


def _target_keyword_score(profile: PersonaProfile, target: ServiceSpec | AgentConcept | None) -> float | None:
    terms = _target_terms(target)
    if not terms:
        return None
    source_fields = dict(profile.metadata.get("source_fields") or {})
    text = " ".join(
        [
            profile.summary,
            profile.segment,
            " ".join(str(value) for value in source_fields.values()),
        ]
    ).lower()
    hits = sum(1 for term in terms if term in text)
    return round(min(1.0, hits / max(1, len(terms))), 4)


def _target_terms(target: ServiceSpec | AgentConcept | None) -> list[str]:
    if target is None:
        return []
    if isinstance(target, ServiceSpec):
        values = [target.name, target.description, *target.target_users, *target.service_capabilities, *target.known_limits]
    else:
        values = [target.name, target.description, *target.target_users, *target.capabilities, *target.known_limits]
    terms: list[str] = []
    for value in values:
        for token in str(value or "").lower().replace(",", " ").split():
            cleaned = token.strip()
            if len(cleaned) >= 2 and cleaned not in terms:
                terms.append(cleaned)
    return terms[:40]


def _status_from_score(average: float, low_count: int, total: int) -> str:
    if total <= 0:
        return "needs_review"
    if average >= 0.35 and low_count <= max(1, total // 5):
        return "usable_with_review"
    if average >= 0.15:
        return "partial"
    return "needs_review"


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _count(values: Any) -> dict[str, int]:
    return dict(Counter(str(value or "unknown") for value in values).most_common())


def _age_band(value: Any) -> str:
    try:
        age = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if age < 30:
        return "under_30"
    if age < 40:
        return "30s"
    if age < 50:
        return "40s"
    if age < 60:
        return "50s"
    return "60_plus"


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
