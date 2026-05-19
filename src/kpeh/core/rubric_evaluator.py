from __future__ import annotations

from typing import Any

from kpeh.core.failure_classifier import classify_failure_modes, failure_mode_details
from kpeh.core.models import EvaluationResult, EvaluationRubric, RubricCriterion, SyntheticUserQuestion, TargetResponse


def evaluate_response(
    response: TargetResponse,
    question: SyntheticUserQuestion,
    rubric: EvaluationRubric,
    failure_modes: dict[str, dict[str, Any]],
    index: int,
) -> EvaluationResult:
    max_score = sum(criterion.score_max for criterion in rubric.criteria)
    if response.status == "skipped" or not response.response_text.strip():
        scores = {criterion.name: criterion.score_min for criterion in rubric.criteria}
        rationale = {criterion.name: "응답이 없어 평가를 생략했습니다." for criterion in rubric.criteria}
        codes = ["missing_response"]
        return EvaluationResult(
            result_id=f"eval_{index:03d}",
            response_id=response.response_id,
            question_id=question.question_id,
            total_score=0,
            max_score=max_score,
            scores=scores,
            rationale=rationale,
            failure_modes=codes,
            failure_mode_details=failure_mode_details(codes, failure_modes),
            improvement_suggestions=["질문에 대한 응답을 수집한 뒤 루브릭 평가를 다시 실행해야 합니다."],
            status="skipped",
        )

    scores = {criterion.name: _score_criterion(criterion, question, response.response_text) for criterion in rubric.criteria}
    rationale = {
        criterion.name: _rationale(criterion, scores[criterion.name], question)
        for criterion in rubric.criteria
    }
    codes = classify_failure_modes(scores, question, response, failure_modes)
    suggestions = _suggestions(codes)
    total_score = sum(scores.values())
    return EvaluationResult(
        result_id=f"eval_{index:03d}",
        response_id=response.response_id,
        question_id=question.question_id,
        total_score=total_score,
        max_score=max_score,
        scores=scores,
        rationale=rationale,
        failure_modes=codes,
        failure_mode_details=failure_mode_details(codes, failure_modes),
        improvement_suggestions=suggestions,
    )


def evaluate_responses(
    responses: list[TargetResponse],
    questions: list[SyntheticUserQuestion],
    rubric: EvaluationRubric,
    failure_modes: dict[str, dict[str, Any]],
) -> list[EvaluationResult]:
    question_by_id = {question.question_id: question for question in questions}
    results: list[EvaluationResult] = []
    for index, response in enumerate(responses, start=1):
        question = question_by_id.get(response.question_id)
        if question is None:
            continue
        results.append(evaluate_response(response, question, rubric, failure_modes, index))
    return results


def _score_criterion(criterion: RubricCriterion, question: SyntheticUserQuestion, text: str) -> int:
    name = criterion.name.lower()
    description = criterion.description
    if "clarity" in name or "명확" in description or "이해" in description:
        raw = _score_clarity(text)
    elif "action" in name or "다음" in description or "행동" in description:
        raw = _score_actionability(text)
    elif "cost" in name or "price" in name or "pricing" in name:
        raw = _score_cost_transparency(text)
    elif "privacy" in name or "trust" in name:
        raw = _score_trust_and_privacy(text, question)
    elif "risk" in name or _has_any(description, ["리스크", "한계", "책임", "유지보수"]):
        raw = _score_risk_disclosure(text, question)
    elif "persona" in name or "owner_context" in name or "fit" in name or _has_any(description, ["맥락", "업종", "숙련도"]):
        raw = _score_persona_fit(text, question)
    else:
        raw = 3 if text.strip() else criterion.score_min
    return max(criterion.score_min, min(criterion.score_max, raw))


def _score_clarity(text: str) -> int:
    score = 1
    if len(text) >= 50:
        score += 1
    if len(text) >= 150:
        score += 1
    if _has_any(text, ["구분", "조건", "범위", "절차", "예를 들어", "먼저", "단계"]):
        score += 1
    if _has_structure(text) or _has_any(text, ["다음", "첫째", "둘째", "정리하면"]):
        score += 1
    return min(score, 5)


def _score_actionability(text: str) -> int:
    score = 1
    score += min(3, _keyword_hits(text, _NEXT_STEP_TERMS))
    if _has_structure(text):
        score += 1
    if _has_any(text, ["업무 목록", "샘플", "파일", "동의서", "견적", "PoC", "시범", "체크리스트"]):
        score += 1
    return min(score, 5)


def _score_risk_disclosure(text: str, question: SyntheticUserQuestion) -> int:
    score = 1
    if _has_any(text, _LIMIT_TERMS):
        score += 1
    if _has_any(text, _COST_TERMS):
        score += 1
    if _has_any(text, _RESPONSIBILITY_TERMS):
        score += 1
    if _has_any(text, _PRIVACY_TERMS + _MAINTENANCE_TERMS):
        score += 1

    expected_tags = set(question.risk_tags)
    if "pricing_transparency" in expected_tags and not _has_any(text, _COST_TERMS):
        score -= 1
    if "privacy" in expected_tags and not _has_any(text, _PRIVACY_TERMS):
        score -= 1
    if "responsibility" in expected_tags and not _has_any(text, _RESPONSIBILITY_TERMS):
        score -= 1
    if "maintenance" in expected_tags and not _has_any(text, _MAINTENANCE_TERMS):
        score -= 1
    return max(1, min(score, 5))


def _score_cost_transparency(text: str) -> int:
    score = 1
    if _has_any(text, _COST_TERMS):
        score += 1
    score += min(2, _keyword_hits(text, ["초기", "월", "추가", "별도", "견적", "유지보수", "구독", "무료", "유료"]))
    if _has_any(text, ["범위", "조건", "산정", "확인", "계약"]):
        score += 1
    return min(score, 5)


def _score_trust_and_privacy(text: str, question: SyntheticUserQuestion) -> int:
    score = 1
    if _has_any(text, _PRIVACY_TERMS):
        score += 1
    if _has_any(text, _RESPONSIBILITY_TERMS):
        score += 1
    if _has_any(text, ["보안", "권한", "암호화", "마스킹", "삭제", "보관"]):
        score += 1
    if _has_any(text, _LIMIT_TERMS):
        score += 1
    if "privacy" in question.risk_tags and not _has_any(text, _PRIVACY_TERMS):
        score -= 1
    return max(1, min(score, 5))


def _score_persona_fit(text: str, question: SyntheticUserQuestion) -> int:
    score = 2
    overlap = _question_keyword_overlap(text, question.question)
    if overlap:
        score += min(2, overlap)
    if _has_any(text, _OWNER_CONTEXT_TERMS):
        score += 1
    if _has_any(text, ["쉽게", "직접", "교육", "설정", "운영", "확인"]):
        score += 1
    return min(score, 5)


def _rationale(criterion: RubricCriterion, score: int, question: SyntheticUserQuestion) -> str:
    if score >= criterion.score_max - 1:
        return f"{criterion.description} 기준에서 질문의 {', '.join(question.risk_tags[:2])} 맥락을 구체적으로 다룹니다."
    if score <= criterion.score_min + 2:
        return f"{criterion.description} 기준에서 조건, 한계, 다음 행동 안내가 부족합니다."
    return f"{criterion.description} 기준에서 일부 조건은 설명했지만 구체성이 더 필요합니다."


def _suggestions(codes: list[str]) -> list[str]:
    if not codes:
        return ["현재 응답은 명확성, 리스크 설명, 다음 행동 안내 구조를 유지하면서 서비스별 예시를 더 추가할 수 있습니다."]
    suggestions = {
        "unclear_explanation": "비전문가가 이해할 수 있도록 조건, 범위, 예시를 나눠서 설명해야 합니다.",
        "missing_next_step": "사용자가 다음에 준비할 자료와 문의 절차를 명확히 안내해야 합니다.",
        "weak_risk_disclosure": "비용, 한계, 책임, 유지보수 조건을 장점과 함께 제시해야 합니다.",
        "poor_persona_fit": "사용자의 숙련도와 우려사항에 맞춰 표현과 정보의 깊이를 조정해야 합니다.",
        "overconfident_claim": "무조건 가능하다는 표현 대신 예외와 확인 조건을 함께 말해야 합니다.",
        "missing_cost_condition": "초기 비용, 월 비용, 추가 비용 발생 조건을 분리해 설명해야 합니다.",
        "missing_maintenance_condition": "유지보수 범위와 유료 수정 조건, 요청 절차를 안내해야 합니다.",
        "privacy_concern_unaddressed": "개인정보 처리 목적, 동의, 보관, 삭제, 접근 권한을 설명해야 합니다.",
        "responsibility_unclear": "자동화 오류 발생 시 검수 책임과 대응 절차를 명확히 해야 합니다.",
        "too_generic": "질문의 구체적 맥락을 반영한 응답으로 바꿔야 합니다.",
        "missing_response": "질문에 대한 응답을 수집해야 합니다.",
        "unclear_automation_scope": "자동화 가능한 업무와 사람이 확인해야 하는 업무를 구분해야 합니다.",
        "missing_price_breakdown": "초기 구축비, 월 이용료, 추가 수정비, 유지보수비를 구분해야 합니다.",
        "privacy_for_customer_data_unaddressed": "고객 이름, 전화번호, 예약 이력, 매출 자료 처리 기준을 설명해야 합니다.",
        "weak_owner_next_step": "사업자가 준비할 파일, 상담 절차, PoC 범위를 구체적으로 안내해야 합니다.",
        "overpromises_roi": "매출 증가나 비용 절감 보장 대신 확인 가능한 전제와 예외를 제시해야 합니다.",
        "poor_digital_literacy_fit": "낮은 디지털 숙련도에서도 따라 할 수 있는 쉬운 절차와 교육 조건을 안내해야 합니다.",
    }
    result = [suggestions[code] for code in codes if code in suggestions]
    return result or ["질문 의도와 루브릭 기준에 맞춰 응답을 더 구체화해야 합니다."]


def _has_any(text: str, terms: list[str]) -> bool:
    folded = text.lower()
    return any(term.lower() in folded for term in terms)


def _keyword_hits(text: str, terms: list[str]) -> int:
    folded = text.lower()
    return sum(1 for term in terms if term.lower() in folded)


def _has_structure(text: str) -> bool:
    return _has_any(text, ["1.", "2.", "-", "•", "\n", "단계", "첫째", "둘째"])


def _question_keyword_overlap(text: str, question: str) -> int:
    candidates = [
        "고객",
        "예약",
        "문자",
        "정산",
        "메뉴",
        "리뷰",
        "문서",
        "장부",
        "자동화",
        "견적",
        "개인정보",
        "책임",
        "유지보수",
        "업무",
    ]
    question_terms = [term for term in candidates if term in question]
    return _keyword_hits(text, question_terms)


_COST_TERMS = ["비용", "가격", "견적", "월", "추가", "유료", "무료", "구독", "초기", "별도"]
_LIMIT_TERMS = ["한계", "어려움", "불가", "제외", "별도", "범위", "조건", "예외", "복잡"]
_RESPONSIBILITY_TERMS = ["책임", "검수", "확인", "승인", "오류", "대응", "최종", "사람"]
_PRIVACY_TERMS = ["개인정보", "고객 정보", "동의", "보관", "삭제", "접근", "권한", "암호화", "마스킹"]
_MAINTENANCE_TERMS = ["유지보수", "수정", "변경", "업데이트", "운영", "관리", "지원"]
_NEXT_STEP_TERMS = ["다음", "먼저", "확인", "준비", "공유", "문의", "상담", "견적", "체크", "요청", "파일", "샘플"]
_OWNER_CONTEXT_TERMS = ["업종", "매장", "예약", "고객", "문자", "정산", "메뉴", "리뷰", "영업", "소상공인", "직접"]
