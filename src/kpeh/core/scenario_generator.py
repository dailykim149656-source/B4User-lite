from __future__ import annotations

from kpeh.core.models import EvaluationScenario, PersonaProfile, ServiceSpec


def generate_scenario(profile: PersonaProfile, service: ServiceSpec, index: int) -> EvaluationScenario:
    concern_names = [concern.name for concern in profile.likely_concerns]
    primary = concern_names[0] if concern_names else "도입 적합성"
    secondary = concern_names[1] if len(concern_names) > 1 else "실행 조건"
    risk_context = _dedupe(concern_names + service.known_limits[:2])
    return EvaluationScenario(
        scenario_id=f"scn_{index:03d}",
        profile_id=profile.profile_id,
        service_id=service.service_id,
        situation=(
            f"{profile.summary} {service.name} 도입을 검토하면서 "
            f"{primary}과 {secondary}을 확인하려는 상황. 서비스 설명: {service.description}"
        ),
        user_goal=f"{service.name}이 본인의 상황에 실제로 적합한지 확인하고 싶다.",
        context={
            "budget_sensitivity": _budget_sensitivity(profile),
            "technical_confidence": _technical_confidence(profile),
            "risk_context": risk_context[:5] or ["도입 조건 불확실성"],
        },
    )


def generate_scenarios(profiles: list[PersonaProfile], service: ServiceSpec) -> list[EvaluationScenario]:
    return [generate_scenario(profile, service, index) for index, profile in enumerate(profiles, start=1)]


def _budget_sensitivity(profile: PersonaProfile) -> str:
    income = str(profile.metadata.get("source_fields", {}).get("income_band", "")).lower()
    if income in {"low", "lower", "낮음"}:
        return "high"
    if income in {"high", "upper", "높음"}:
        return "low"
    return "medium"


def _technical_confidence(profile: PersonaProfile) -> str:
    literacy = str(profile.metadata.get("source_fields", {}).get("digital_literacy", "")).lower()
    if literacy in {"low", "medium_low", "낮음"}:
        return "low"
    if literacy in {"high", "높음"}:
        return "high"
    return "medium"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
