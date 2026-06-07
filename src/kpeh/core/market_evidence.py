from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kpeh.core.io_utils import ensure_parent_dir, write_json
from kpeh.core.models import AgentConcept, ServiceSpec, to_plain_data


SYNTHETIC_MARKET_NOTICE = (
    "Market evidence is directional. It can strengthen or weaken a synthetic "
    "marketability hypothesis, but it is not proof of demand by itself."
)

SECRET_KEYS = {"api_key", "apikey", "secret", "client_secret", "token", "password", "credential", "credentials"}

DEMAND_SIGNALS = {
    "search_trend",
    "search_volume",
    "keyword_volume",
    "related_keyword",
    "trend_index",
    "impressions_estimate",
}
OWNED_TRAFFIC_SIGNALS = {"impressions", "clicks", "ctr", "position", "site_visit", "organic_clicks"}
CONVERSION_SIGNALS = {
    "signup",
    "signup_rate",
    "waitlist",
    "lead",
    "demo_request",
    "consultation_request",
    "conversion",
    "conversion_rate",
}
PAID_OR_PILOT_SIGNALS = {"payment", "revenue", "paid_pilot", "pilot", "contract", "retention", "repeat_usage"}
INTENT_SIGNALS = {"cpc", "competition", "top_of_page_bid", "purchase_intent", "commercial_intent"}


@dataclass(slots=True)
class MarketEvidenceRecord:
    source: str
    signal_type: str
    label: str
    value: float | None = None
    period: str | None = None
    region: str | None = None
    segment: str | None = None
    intent: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketEvidenceRecord":
        clean = _sanitize(data)
        signal_type = str(
            clean.get("signal_type")
            or clean.get("metric")
            or clean.get("type")
            or clean.get("category")
            or "unknown"
        )
        label = str(clean.get("label") or clean.get("keyword") or clean.get("query") or clean.get("name") or signal_type)
        known = {
            "source",
            "signal_type",
            "metric",
            "type",
            "category",
            "label",
            "keyword",
            "query",
            "name",
            "value",
            "period",
            "region",
            "segment",
            "intent",
            "notes",
        }
        metadata = {key: value for key, value in clean.items() if key not in known and value not in (None, "", [], {})}
        return cls(
            source=str(clean.get("source") or "manual"),
            signal_type=_normalize_signal_type(signal_type),
            label=label,
            value=_optional_float(clean.get("value")),
            period=_optional_str(clean.get("period")),
            region=_optional_str(clean.get("region")),
            segment=_optional_str(clean.get("segment")),
            intent=_optional_str(clean.get("intent")),
            notes=_optional_str(clean.get("notes")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


def load_market_evidence(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    records = _load_records(Path(path))
    return build_market_evidence_summary(records)


def write_market_evidence(path: str | Path, evidence: dict[str, Any]) -> None:
    write_json(path, evidence)


def write_market_evidence_report(path: str | Path, evidence: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    Path(path).write_text("\n".join(markdown_lines_from_market_evidence(evidence)), encoding="utf-8", newline="\n")


def build_market_evidence_summary(records: list[MarketEvidenceRecord]) -> dict[str, Any]:
    signal_counts = Counter(record.signal_type for record in records)
    source_counts = Counter(record.source for record in records)
    level = _evidence_level(records)
    return {
        "notice": SYNTHETIC_MARKET_NOTICE,
        "record_count": len(records),
        "source_count": len(source_counts),
        "sources": dict(source_counts.most_common()),
        "signal_counts": dict(signal_counts.most_common()),
        "evidence_level": level,
        "top_signals": _top_signals(records),
        "claim_limit": _claim_limit(level),
        "warnings": _warnings(records, level),
        "records": [record.to_dict() for record in records],
    }


def build_report_decision_brief(
    *,
    evaluation_mode: str,
    target: ServiceSpec | AgentConcept | None,
    synthetic_score: float | None = None,
    selection_audit: dict[str, Any] | None = None,
    market_evidence: dict[str, Any] | None = None,
    top_strengths: list[str] | None = None,
    top_risks: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    evidence = market_evidence or build_market_evidence_summary([])
    evidence_level = dict(evidence.get("evidence_level") or {})
    selection_decision = dict((selection_audit or {}).get("validation_decision") or {})
    score = float(synthetic_score or 0.0)
    risks = list(top_risks or [])
    strengths = list(top_strengths or [])
    actions = list(next_actions or [])
    decision = _recommended_decision(score, evidence_level, selection_decision, risks)
    confidence = _brief_confidence(evidence_level, selection_decision, score)
    target_name = getattr(target, "name", None) or "untitled target"
    return {
        "target_name": target_name,
        "evaluation_mode": evaluation_mode,
        "recommended_decision": decision,
        "confidence": confidence,
        "synthetic_score": round(score, 2),
        "evidence_level": evidence_level,
        "claim_limit": evidence.get("claim_limit"),
        "strongest_evidence": _first_non_empty(
            strengths,
            [str(item.get("summary")) for item in evidence.get("top_signals") or []],
            ["Synthetic evaluation completed; external market evidence is not yet attached."],
        )[:3],
        "biggest_risks": _first_non_empty(
            risks,
            list(selection_decision.get("blocking_issues") or []),
            ["No real conversion evidence is attached."],
        )[:3],
        "next_actions": _first_non_empty(
            actions,
            list(evidence_level.get("next_actions") or []),
            ["Attach search, traffic, or conversion evidence before making marketability claims."],
        )[:5],
        "why_this_may_be_wrong": _why_this_may_be_wrong(selection_audit, evidence),
        "claim_ledger": _claim_ledger(evaluation_mode, score, selection_audit, evidence),
    }


def markdown_lines_from_decision_brief(brief: dict[str, Any], *, heading_level: int = 2) -> list[str]:
    prefix = "#" * heading_level
    evidence_level = dict(brief.get("evidence_level") or {})
    lines = [
        f"{prefix} Decision Brief",
        "",
        "- target: {target}".format(target=brief.get("target_name", "untitled target")),
        "- recommended_decision: {decision}".format(decision=brief.get("recommended_decision", "review")),
        "- confidence: {confidence}".format(confidence=brief.get("confidence", "low")),
        "- synthetic_score: {score}".format(score=brief.get("synthetic_score", 0)),
        "- evidence_level: {level} ({label})".format(
            level=evidence_level.get("level", "L0"),
            label=evidence_level.get("label", "synthetic_only"),
        ),
        "- claim_limit: {claim_limit}".format(claim_limit=brief.get("claim_limit", "synthetic hypothesis only")),
        "",
        f"{prefix}# Strongest Evidence",
        "",
    ]
    for item in brief.get("strongest_evidence") or []:
        lines.append(f"- {item}")
    lines.extend(["", f"{prefix}# Biggest Risks", ""])
    for item in brief.get("biggest_risks") or []:
        lines.append(f"- {item}")
    lines.extend(["", f"{prefix}# Next Validation Steps", ""])
    for item in brief.get("next_actions") or []:
        lines.append(f"- {item}")
    lines.extend(["", f"{prefix}# Claim Ledger", ""])
    for item in brief.get("claim_ledger") or []:
        lines.append("- claim: {claim}".format(claim=item.get("claim")))
        lines.append("  - allowed_wording: {wording}".format(wording=item.get("allowed_wording")))
        lines.append("  - confidence: {confidence}".format(confidence=item.get("confidence")))
        lines.append("  - evidence: {evidence}".format(evidence="; ".join(str(value) for value in item.get("evidence", []))))
        if item.get("not_allowed"):
            lines.append("  - not_allowed: {not_allowed}".format(not_allowed=item.get("not_allowed")))
    lines.extend(["", f"{prefix}# Why This May Be Wrong", ""])
    for item in brief.get("why_this_may_be_wrong") or []:
        lines.append(f"- {item}")
    lines.append("")
    return lines


def markdown_lines_from_market_evidence(evidence: dict[str, Any], *, heading_level: int = 2) -> list[str]:
    prefix = "#" * heading_level
    level = dict(evidence.get("evidence_level") or {})
    lines = [
        f"{prefix} Market Evidence",
        "",
        f"> {evidence.get('notice') or SYNTHETIC_MARKET_NOTICE}",
        "",
        "- record_count: {count}".format(count=evidence.get("record_count", 0)),
        "- source_count: {count}".format(count=evidence.get("source_count", 0)),
        "- evidence_level: {level} ({label})".format(level=level.get("level", "L0"), label=level.get("label", "synthetic_only")),
        "- claim_limit: {claim_limit}".format(claim_limit=evidence.get("claim_limit", "synthetic hypothesis only")),
        "",
        f"{prefix}# Top Signals",
        "",
    ]
    for item in evidence.get("top_signals") or []:
        lines.append("- {summary}".format(summary=item.get("summary")))
    if not evidence.get("top_signals"):
        lines.append("- No external market evidence is attached.")
    warnings = list(evidence.get("warnings") or [])
    if warnings:
        lines.extend(["", f"{prefix}# Evidence Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return lines


def _load_records(path: Path) -> list[MarketEvidenceRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Market evidence file not found: {path}")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return [MarketEvidenceRecord.from_dict(row) for row in rows]
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        raw_rows = data.get("records") or data.get("evidence") or data.get("signals") or []
        rows = raw_rows if isinstance(raw_rows, list) else []
    else:
        rows = []
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Market evidence rows must be objects: {path}")
    return [MarketEvidenceRecord.from_dict(row) for row in rows]


def _evidence_level(records: list[MarketEvidenceRecord]) -> dict[str, Any]:
    signals = {record.signal_type for record in records}
    if signals & PAID_OR_PILOT_SIGNALS:
        return {
            "level": "L4",
            "label": "paid_or_pilot_evidence",
            "meaning": "There is payment, pilot, revenue, contract, retention, or repeat-use evidence.",
            "next_actions": ["Validate repeatability by segment and compare against acquisition cost."],
        }
    if signals & CONVERSION_SIGNALS:
        return {
            "level": "L3",
            "label": "conversion_evidence",
            "meaning": "There is signup, waitlist, lead, demo, consultation, or conversion evidence.",
            "next_actions": ["Run a follow-up test that measures qualified leads or paid pilot intent."],
        }
    if signals & OWNED_TRAFFIC_SIGNALS:
        return {
            "level": "L2",
            "label": "owned_traffic_evidence",
            "meaning": "There is owned traffic evidence such as Search Console impressions, clicks, or site visits.",
            "next_actions": ["Connect traffic to landing conversion before making marketability claims."],
        }
    if signals & (DEMAND_SIGNALS | INTENT_SIGNALS):
        return {
            "level": "L1",
            "label": "search_or_intent_evidence",
            "meaning": "There is search, trend, CPC, competition, or keyword evidence.",
            "next_actions": ["Validate whether search interest converts into a signup, inquiry, or pilot request."],
        }
    return {
        "level": "L0",
        "label": "synthetic_only",
        "meaning": "No external market evidence is attached.",
        "next_actions": ["Attach keyword, traffic, conversion, or pilot evidence."],
    }


def _claim_limit(level: dict[str, Any]) -> str:
    level_id = str(level.get("level") or "L0")
    return {
        "L0": "Only synthetic product-discovery hypotheses are allowed. Do not claim marketability.",
        "L1": "You may claim directional demand signals, not market validation.",
        "L2": "You may claim owned-traffic interest, not conversion or purchase validation.",
        "L3": "You may claim early conversion evidence, with segment and sample-size caveats.",
        "L4": "You may claim stronger pilot or paid evidence, while still avoiding broad market forecasts.",
    }.get(level_id, "Treat findings as directional and review evidence quality.")


def _recommended_decision(
    score: float,
    evidence_level: dict[str, Any],
    selection_decision: dict[str, Any],
    risks: list[str],
) -> str:
    level = str(evidence_level.get("level") or "L0")
    selection_status = str(selection_decision.get("status") or "")
    if selection_status == "insufficient_for_target_claims":
        return "rebuild_panel_before_claims"
    if level in {"L0", "L1"}:
        return "narrow_and_test"
    if score >= 70 and level in {"L3", "L4"} and len(risks) <= 2:
        return "go_with_validation_gate"
    if score < 45:
        return "rethink_positioning"
    return "conditional_go"


def _brief_confidence(evidence_level: dict[str, Any], selection_decision: dict[str, Any], score: float) -> str:
    level = str(evidence_level.get("level") or "L0")
    if selection_decision.get("status") == "insufficient_for_target_claims" or level == "L0":
        return "low"
    if level in {"L3", "L4"} and score >= 60:
        return "medium"
    return "medium-low"


def _why_this_may_be_wrong(selection_audit: dict[str, Any] | None, evidence: dict[str, Any]) -> list[str]:
    reasons = [
        "Synthetic personas may not represent real buyer distribution or budget authority.",
        "Search or trend interest can reflect curiosity, not willingness to pay.",
        "High synthetic scores can hide switching cost, trust, privacy, or workflow constraints.",
    ]
    if not evidence or dict(evidence.get("evidence_level") or {}).get("level") in {None, "L0", "L1"}:
        reasons.append("The evidence does not yet include real conversion, paid pilot, or retention behavior.")
    decision = dict((selection_audit or {}).get("validation_decision") or {})
    for issue in decision.get("blocking_issues") or []:
        reasons.append(f"Persona selection blocking issue: {issue}.")
    for issue in list(decision.get("review_issues") or [])[:3]:
        reasons.append(f"Persona selection review issue: {issue}.")
    return _dedupe(reasons)[:7]


def _claim_ledger(
    evaluation_mode: str,
    score: float,
    selection_audit: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    level = dict(evidence.get("evidence_level") or {})
    selection_status = dict((selection_audit or {}).get("validation_decision") or {}).get("status", "not_available")
    return [
        {
            "claim": "The target deserves further product discovery.",
            "allowed_wording": "There is a synthetic hypothesis worth testing.",
            "confidence": "medium-low" if score >= 55 else "low",
            "evidence": [f"synthetic_score={round(score, 2)}", f"selection_status={selection_status}"],
            "not_allowed": "This proves market demand.",
        },
        {
            "claim": "The market shows real demand.",
            "allowed_wording": _claim_limit(level),
            "confidence": _confidence_for_level(str(level.get("level") or "L0")),
            "evidence": [f"evidence_level={level.get('level', 'L0')}", f"record_count={evidence.get('record_count', 0)}"],
            "not_allowed": "Marketability is validated without conversion or paid evidence.",
        },
        {
            "claim": f"{evaluation_mode} findings can guide the next experiment.",
            "allowed_wording": "Use the report to choose the next validation test and message variant.",
            "confidence": "medium",
            "evidence": ["bounded synthetic evaluation", "claim limits attached"],
            "not_allowed": "Use the report as real user research.",
        },
    ]


def _confidence_for_level(level: str) -> str:
    if level in {"L3", "L4"}:
        return "medium"
    if level == "L2":
        return "medium-low"
    return "low"


def _top_signals(records: list[MarketEvidenceRecord], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(records, key=lambda record: (_signal_priority(record.signal_type), record.value or 0), reverse=True)
    result = []
    for record in ranked[:limit]:
        value = "" if record.value is None else f" value={record.value:g}"
        period = "" if not record.period else f" period={record.period}"
        result.append(
            {
                "source": record.source,
                "signal_type": record.signal_type,
                "label": record.label,
                "summary": f"{record.source}:{record.signal_type}:{record.label}{value}{period}",
            }
        )
    return result


def _signal_priority(signal_type: str) -> int:
    if signal_type in PAID_OR_PILOT_SIGNALS:
        return 5
    if signal_type in CONVERSION_SIGNALS:
        return 4
    if signal_type in OWNED_TRAFFIC_SIGNALS:
        return 3
    if signal_type in INTENT_SIGNALS:
        return 2
    if signal_type in DEMAND_SIGNALS:
        return 1
    return 0


def _warnings(records: list[MarketEvidenceRecord], level: dict[str, Any]) -> list[str]:
    warnings = []
    if not records:
        warnings.append("No market evidence was provided; marketability claims must stay synthetic.")
    if str(level.get("level") or "L0") in {"L0", "L1", "L2"}:
        warnings.append("Evidence is below conversion level; do not claim validated market demand.")
    if any(record.value is None for record in records):
        warnings.append("Some evidence rows do not include numeric values; treat them as qualitative signals.")
    return warnings


def _normalize_signal_type(value: str) -> str:
    text = str(value or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "search_console_impressions": "impressions",
        "search_console_clicks": "clicks",
        "google_trends": "search_trend",
        "naver_datalab": "search_trend",
        "keyword": "related_keyword",
        "lead_form": "lead",
        "demo": "demo_request",
        "consultation": "consultation_request",
        "paid": "payment",
    }
    return aliases.get(text, text or "unknown")


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    clean = {}
    for key, value in data.items():
        normalized = str(key).strip()
        if normalized.lower() in SECRET_KEYS:
            continue
        clean[normalized] = value
    return clean


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _first_non_empty(*groups: list[str]) -> list[str]:
    for group in groups:
        values = [str(value) for value in group if str(value)]
        if values:
            return values
    return []


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
