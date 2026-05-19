from __future__ import annotations

import random

from kpeh.core.models import EvaluationScenario, PersonaProfile, ServiceSpec, SyntheticUserQuestion
from kpeh.core.persona_lens import PersonaLens, build_persona_lens


QUESTION_TEMPLATES = {
    "maintenance": {
        "question": "{capability} 방식을 나중에 바꾸면 수정이나 유지보수는 어떻게 진행되나요?",
        "intent": "유지보수 범위 확인",
        "traits": [
            "유지보수 범위를 명확히 설명한다",
            "추가 비용 발생 조건을 설명한다",
            "수정 요청 절차를 안내한다",
        ],
        "tags": ["maintenance", "pricing_transparency", "actionability"],
    },
    "cost": {
        "question": "처음 도입할 때 드는 비용과 매달 계속 드는 비용을 구분해서 설명해 줄 수 있나요?",
        "intent": "비용 조건 확인",
        "traits": [
            "초기 비용과 반복 비용을 구분한다",
            "추가 비용 조건을 숨기지 않는다",
            "견적 확인 방법을 안내한다",
        ],
        "tags": ["pricing_transparency", "risk_disclosure", "actionability"],
    },
    "privacy": {
        "question": "고객 이름이나 전화번호 같은 개인정보가 들어간 자료를 맡겨도 안전한가요?",
        "intent": "개인정보 처리 조건 확인",
        "traits": [
            "개인정보 처리 범위와 동의 조건을 설명한다",
            "보관, 접근, 삭제 기준을 안내한다",
            "불가능하거나 별도 확인이 필요한 부분을 말한다",
        ],
        "tags": ["privacy", "risk_disclosure", "actionability"],
    },
    "responsibility": {
        "question": "자동화가 잘못 처리해서 고객에게 문제가 생기면 책임은 누구에게 있나요?",
        "intent": "책임 소재 확인",
        "traits": [
            "자동화의 한계와 검수 책임을 설명한다",
            "문제 발생 시 대응 절차를 안내한다",
            "과도한 보장을 하지 않는다",
        ],
        "tags": ["responsibility", "risk_disclosure", "overconfidence"],
    },
    "usability": {
        "question": "제가 컴퓨터를 잘 못해도 직접 설정하고 계속 사용할 수 있을까요?",
        "intent": "사용 쉬움 확인",
        "traits": [
            "초기 설정과 운영 난이도를 쉽게 설명한다",
            "지원 방식과 교육 필요 여부를 안내한다",
            "사용자가 할 일과 맡길 일을 구분한다",
        ],
        "tags": ["persona_fit", "usability", "actionability"],
    },
    "limit": {
        "question": "어떤 업무는 자동화가 어렵거나 별도 견적이 필요한지 미리 알 수 있을까요?",
        "intent": "서비스 한계 확인",
        "traits": [
            "가능한 업무와 어려운 업무를 구분한다",
            "별도 견적이나 확인이 필요한 조건을 설명한다",
            "다음 확인 절차를 안내한다",
        ],
        "tags": ["service_limit", "risk_disclosure", "actionability"],
    },
}


def generate_questions(
    scenarios: list[EvaluationScenario],
    profiles: list[PersonaProfile],
    service: ServiceSpec,
    questions_per_scenario: int = 2,
    seed: int | None = None,
) -> list[SyntheticUserQuestion]:
    if questions_per_scenario < 1 or questions_per_scenario > 3:
        raise ValueError("questions_per_scenario must be between 1 and 3")
    rng = random.Random(seed)
    profile_by_id = {profile.profile_id: profile for profile in profiles}
    questions: list[SyntheticUserQuestion] = []
    for scenario in scenarios:
        profile = profile_by_id.get(scenario.profile_id)
        kinds = _question_kinds(scenario, profile)
        rng.shuffle(kinds)
        selected = kinds[:questions_per_scenario]
        for kind in selected:
            template = QUESTION_TEMPLATES[kind]
            question_id = f"q_{len(questions) + 1:03d}"
            questions.append(
                SyntheticUserQuestion(
                    question_id=question_id,
                    scenario_id=scenario.scenario_id,
                    profile_id=scenario.profile_id,
                    question=_personalized_question(
                        kind,
                        template["question"].format(capability=_primary_capability(service)),
                        scenario,
                        profile,
                    ),
                    intent=template["intent"],
                    difficulty=_difficulty(kind),
                    expected_good_answer_traits=_expected_traits(template["traits"], profile),
                    risk_tags=list(template["tags"]),
                )
            )
    return questions


def _personalized_question(
    kind: str,
    base_question: str,
    scenario: EvaluationScenario,
    profile: PersonaProfile | None,
) -> str:
    if profile is None:
        return base_question
    lens = build_persona_lens(profile)
    parts = [
        f"제 배경: {_compact_sentence(profile.summary)}.",
        f"제 업무 핵심은 {lens.work_context}입니다.",
        _concern_sentence(profile),
        _context_sentence(scenario),
        _question_body(kind, base_question, lens),
    ]
    return " ".join(part for part in parts if part)


def _expected_traits(base_traits: list[str], profile: PersonaProfile | None) -> list[str]:
    traits = list(base_traits)
    if profile is None:
        return traits
    if profile.communication_style:
        traits.append(f"persona communication style에 맞춰 설명한다: {profile.communication_style}")
    if profile.likely_concerns:
        concerns = ", ".join(concern.name for concern in profile.likely_concerns[:2])
        traits.append(f"persona의 주요 우려를 직접 다룬다: {concerns}")
    lens = build_persona_lens(profile)
    traits.append(f"persona 업무 맥락을 반영한다: {lens.work_context}")
    traits.append(f"persona 판단 근거를 제시한다: {lens.proof_need}")
    return traits


def _question_body(kind: str, base_question: str, lens: PersonaLens) -> str:
    if kind == "cost":
        return (
            f"첫 단계가 '{lens.first_step}'이라면 초기 세팅비, 월 비용, 추가 비용, 해지 조건을 "
            f"{lens.value_metric} 기준으로 어떻게 비교하면 될까요?"
        )
    if kind == "privacy":
        return (
            f"{lens.work_context}에 고객 정보나 내부 자료가 들어갈 때, "
            f"{lens.proof_need}를 어떤 문서나 화면으로 확인할 수 있나요?"
        )
    if kind == "responsibility":
        return (
            f"{lens.work_context} 자동화가 잘못 처리되면 누가 확인하고 복구하나요? "
            f"이 우려({lens.objection_angle})에 대한 책임 범위도 같이 설명해 줄 수 있나요?"
        )
    if kind == "usability":
        return (
            f"{lens.first_step} 이후에 제가 실제로 배워야 하는 작업은 어디까지인가요? "
            f"{lens.support_need}가 제공되는지도 확인할 수 있을까요?"
        )
    if kind == "maintenance":
        return (
            f"업무 맥락이 '{lens.work_context}'에서 바뀌거나 양식이 달라질 때 수정 요청은 어떻게 넣나요? "
            f"{lens.support_need}와 추가 비용 발생 기준을 함께 알 수 있을까요?"
        )
    if kind == "limit":
        return (
            f"{lens.work_context} 중 자동화하기 어려운 부분은 무엇인가요? "
            f"{lens.proof_need}로 먼저 확인한 뒤 진행할 수 있을까요?"
        )
    return base_question


def _compact_sentence(text: str, *, max_chars: int = 90) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= max_chars:
        return compact.rstrip(".")
    return compact[: max_chars - 1].rstrip() + "…"


def _concern_sentence(profile: PersonaProfile) -> str:
    concerns = [concern.name for concern in profile.likely_concerns[:2] if concern.name]
    if not concerns:
        return ""
    return f"특히 {', '.join(concerns)} 관점에서 확인하고 싶습니다."


def _context_sentence(scenario: EvaluationScenario) -> str:
    budget = str(scenario.context.get("budget_sensitivity") or "")
    technical = str(scenario.context.get("technical_confidence") or "")
    signals: list[str] = []
    if budget == "high":
        signals.append("비용 부담이 큰 상황")
    elif budget == "low":
        signals.append("비용보다 효과 검증을 더 중시하는 상황")
    if technical == "low":
        signals.append("디지털 도구 사용이 익숙하지 않은 상황")
    elif technical == "high":
        signals.append("도구를 직접 비교해볼 수 있는 상황")
    if not signals:
        return ""
    return f"{'이고 '.join(signals)}입니다."


def _question_kinds(scenario: EvaluationScenario, profile: PersonaProfile | None) -> list[str]:
    text = " ".join(str(item) for item in scenario.context.get("risk_context", []))
    concerns = " ".join(concern.name for concern in (profile.likely_concerns if profile else []))
    combined = f"{text} {concerns}"
    kinds: list[str] = []
    if any(token in combined for token in ["유지보수", "수정"]):
        kinds.append("maintenance")
    if any(token in combined for token in ["비용", "가격", "견적"]):
        kinds.append("cost")
    if any(token in combined for token in ["개인정보", "고객"]):
        kinds.append("privacy")
    if any(token in combined for token in ["디지털", "학습", "사용"]):
        kinds.append("usability")
    kinds.extend(["responsibility", "limit", "cost", "maintenance", "privacy", "usability"])
    return _dedupe(kinds)


def _primary_capability(service: ServiceSpec) -> str:
    return service.service_capabilities[0] if service.service_capabilities else service.name


def _difficulty(kind: str) -> str:
    return "hard" if kind in {"privacy", "responsibility"} else "medium"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
