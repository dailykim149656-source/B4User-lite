from __future__ import annotations

from typing import Any

from kpeh.core.models import SyntheticUserQuestion, TargetResponse


def classify_failure_modes(
    scores: dict[str, int],
    question: SyntheticUserQuestion,
    response: TargetResponse,
    failure_modes: dict[str, dict[str, Any]],
) -> list[str]:
    if response.status == "skipped" or not response.response_text.strip():
        return ["missing_response"]

    text = response.response_text
    codes: list[str] = []
    if scores.get("clarity", 5) <= 2:
        codes.append("unclear_explanation")
        codes.append("unclear_automation_scope")
    if scores.get("actionability", 5) <= 2:
        codes.append("missing_next_step")
        codes.append("weak_owner_next_step")
    if scores.get("risk_disclosure", 5) <= 2:
        codes.append("weak_risk_disclosure")
    if scores.get("persona_fit", 5) <= 2:
        codes.append("poor_persona_fit")
    if scores.get("owner_context_fit", 5) <= 2:
        codes.append("poor_digital_literacy_fit")
    if scores.get("cost_transparency", 5) <= 2:
        codes.append("missing_cost_condition")
        codes.append("missing_price_breakdown")
    if scores.get("trust_and_privacy", 5) <= 2:
        codes.append("privacy_concern_unaddressed")
        codes.append("privacy_for_customer_data_unaddressed")
    if len(text) < 90 or _looks_generic(text):
        codes.append("too_generic")
    if _has_tag(question, "pricing") and not _has_any(text, ["비용", "가격", "견적", "월", "추가", "별도"]):
        codes.append("missing_cost_condition")
        codes.append("missing_price_breakdown")
    if "maintenance" in question.risk_tags and not _has_any(text, ["유지보수", "수정", "변경", "범위"]):
        codes.append("missing_maintenance_condition")
    if "privacy" in question.risk_tags and not _has_any(text, ["개인정보", "동의", "보관", "삭제", "접근"]):
        codes.append("privacy_concern_unaddressed")
        codes.append("privacy_for_customer_data_unaddressed")
    if "responsibility" in question.risk_tags and not _has_any(text, ["책임", "검수", "오류", "대응"]):
        codes.append("responsibility_unclear")
    if _has_any(text, ["무조건", "항상", "100%", "절대 문제", "완벽하게", "보장", "전부 자동"]):
        codes.append("overconfident_claim")
        codes.append("overpromises_roi")
    return _dedupe([code for code in codes if code in failure_modes or code == "missing_response"])


def failure_mode_details(codes: list[str], failure_modes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for code in codes:
        definition = failure_modes.get(code, {})
        details.append(
            {
                "code": code,
                "label_ko": definition.get("label_ko") or _fallback_label(code),
                "description": definition.get("description") or "정의되지 않은 실패 유형입니다.",
            }
        )
    return details


def _looks_generic(text: str) -> bool:
    generic_phrases = ["도와드릴 수 있습니다", "가능합니다", "문의해주세요", "상황에 따라 다릅니다"]
    return sum(1 for phrase in generic_phrases if phrase in text) >= 2


def _has_any(text: str, terms: list[str]) -> bool:
    folded = text.lower()
    return any(term.lower() in folded for term in terms)


def _has_tag(question: SyntheticUserQuestion, token: str) -> bool:
    return any(token in tag for tag in question.risk_tags)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _fallback_label(code: str) -> str:
    return {
        "missing_response": "응답 없음",
    }.get(code, code)
