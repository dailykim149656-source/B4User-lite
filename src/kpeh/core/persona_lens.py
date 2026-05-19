from __future__ import annotations

from dataclasses import dataclass

from kpeh.core.models import PersonaProfile


@dataclass(slots=True)
class PersonaLens:
    audience_label: str
    work_context: str
    value_proposition: str
    value_metric: str
    proof_need: str
    support_need: str
    first_step: str
    objection_angle: str
    decision_frame: str


def build_persona_lens(profile: PersonaProfile) -> PersonaLens:
    fields = profile.metadata.get("source_fields", {})
    text = " ".join(
        [
            profile.summary,
            profile.segment,
            profile.communication_style,
            " ".join(concern.name for concern in profile.likely_concerns),
            " ".join(str(value) for value in fields.values()),
        ]
    ).lower()
    digital = str(fields.get("digital_literacy", "")).lower()
    attitude = str(fields.get("technology_attitude", "")).lower()
    income = str(fields.get("income_band", "")).lower()
    age = fields.get("age")
    low_digital = digital in {"low", "medium_low", "낮음"} or (isinstance(age, int) and age >= 60)
    high_digital = digital in {"high", "높음"} or attitude == "enthusiastic"
    cautious = attitude in {"cautious", "skeptical", "보수적"}
    budget_sensitive = income in {"low", "lower", "낮음"}

    work_context, value_proposition, value_metric = _work_context(text)
    proof_need = _proof_need(text, low_digital=low_digital, high_digital=high_digital, budget_sensitive=budget_sensitive)
    support_need = _support_need(text, low_digital=low_digital, high_digital=high_digital, cautious=cautious)
    first_step = _first_step(
        text,
        low_digital=low_digital,
        high_digital=high_digital,
        cautious=cautious,
        budget_sensitive=budget_sensitive,
    )
    objection_angle = _objection_angle(
        text,
        low_digital=low_digital,
        high_digital=high_digital,
        cautious=cautious,
        budget_sensitive=budget_sensitive,
    )
    decision_frame = _decision_frame(
        low_digital=low_digital,
        high_digital=high_digital,
        cautious=cautious,
        budget_sensitive=budget_sensitive,
    )
    return PersonaLens(
        audience_label=_audience_label(profile),
        work_context=work_context,
        value_proposition=value_proposition,
        value_metric=value_metric,
        proof_need=proof_need,
        support_need=support_need,
        first_step=first_step,
        objection_angle=objection_angle,
        decision_frame=decision_frame,
    )


def _work_context(text: str) -> tuple[str, str, str]:
    if any(token in text for token in ["식당", "카페"]):
        return (
            "예약, 쿠폰 문자, 반복 고객 안내",
            "예약 누락과 안내 반복을 줄이는 것",
            "하루 고객 안내 시간과 문자 발송 누락률",
        )
    if any(token in text for token in ["쇼핑몰", "ecommerce"]):
        return (
            "주문 확인과 고객 문자 발송",
            "주문 응대 속도와 고객 문의 부담을 줄이는 것",
            "주문 확인 지연 시간과 반복 문의 감소폭",
        )
    if any(token in text for token in ["학원", "education"]):
        return (
            "출결 안내와 상담 예약",
            "학부모 안내와 상담 예약을 안정적으로 처리하는 것",
            "상담 예약 누락과 출결 안내 재작업 시간",
        )
    if any(token in text for token in ["병원", "원무", "healthcare"]):
        return (
            "예약 안내와 원무 문서 정리",
            "민감한 예약/문서 업무를 안전하게 줄이는 것",
            "예약 안내 오류와 개인정보 취급 단계 수",
        )
    if any(token in text for token in ["세무", "professional_service"]):
        return (
            "고객 자료 정리와 보안 검수",
            "고객 자료 정리 시간을 줄이면서 책임 리스크를 낮추는 것",
            "자료 정리 시간과 검수 누락 건수",
        )
    if "제조 현장" in text or "현장 관리자" in text:
        return (
            "작업 일지와 현장 직원 입력 흐름",
            "현장 기록 정리와 직원 사용 부담을 줄이는 것",
            "작업 일지 정리 시간과 현장 직원 입력 성공률",
        )
    if any(token in text for token in ["제조", "총무", "사무직", "office"]):
        return (
            "엑셀 정리, 보고서, 공지 양식 변경",
            "반복 문서/보고 업무를 줄이는 것",
            "주간 엑셀/보고서 정리 시간",
        )
    if any(token in text for token in ["프리랜서", "디자이너", "creative"]):
        return (
            "고객 문의와 견적서 발송",
            "견적 응답 속도와 고객 커뮤니케이션 품질을 높이는 것",
            "견적서 발송까지 걸리는 시간",
        )
    if any(token in text for token in ["스타트업", "startup", "saas"]):
        return (
            "여러 SaaS 연동과 운영 자동화",
            "기존 도구 사이의 반복 운영 업무를 줄이는 것",
            "수작업 운영 티켓과 자동화 성공률",
        )
    if any(token in text for token in ["철물", "재고"]):
        return (
            "재고 정리와 단골 고객 연락",
            "재고 확인과 고객 연락을 쉽게 정리하는 것",
            "재고 확인 시간과 연락 누락 건수",
        )
    return (
        "반복 업무 정리와 고객 안내",
        "반복 업무 부담을 줄이는 것",
        "반복 업무 처리 시간",
    )


def _proof_need(text: str, *, low_digital: bool, high_digital: bool, budget_sensitive: bool) -> str:
    if any(token in text for token in ["병원", "원무", "학원", "세무", "고객 자료", "보안"]):
        return "동의서, 접근 권한, 보관 기간을 분리한 보안 근거"
    if any(token in text for token in ["제조", "현장", "양식"]):
        return "양식 변경과 예외 처리 사례"
    if high_digital:
        return "기존 도구 연동 범위와 처리 시간 비교 수치"
    if low_digital:
        return "따라 할 수 있는 화면 예시와 교육 시간"
    if budget_sensitive:
        return "최소 범위 가격과 해지 조건"
    return "샘플 업무 진단 결과와 전후 비교"


def _support_need(text: str, *, low_digital: bool, high_digital: bool, cautious: bool) -> str:
    if low_digital:
        return "초기 세팅 대행, 짧은 교육, 전화/메신저 지원"
    if high_digital:
        return "연동 가능 범위, 권한 설정, 성과 대시보드"
    if cautious:
        return "불가능한 업무, 실패 시 복구 절차, 책임 범위"
    if any(token in text for token in ["제조", "총무", "사무"]):
        return "양식 변경 요청과 유지보수 접수 절차"
    return "상담 후 PoC 범위와 다음 행동 안내"


def _first_step(text: str, *, low_digital: bool, high_digital: bool, cautious: bool, budget_sensitive: bool) -> str:
    if budget_sensitive:
        return "최소 기능 범위와 월 고정비를 먼저 확인하는 상담"
    if low_digital:
        return "실제 화면을 보며 대신 세팅해보는 짧은 체험"
    if high_digital:
        return "샘플 데이터로 자동화 흐름을 직접 비교하는 PoC"
    if cautious:
        return "한계와 예외 조건을 먼저 확인하는 진단"
    if any(token in text for token in ["제조", "사무", "총무"]):
        return "현재 쓰는 양식 하나로 자동화 가능성을 보는 샘플 진단"
    return "가장 반복적인 업무 하나를 고르는 샘플 진단"


def _objection_angle(text: str, *, low_digital: bool, high_digital: bool, cautious: bool, budget_sensitive: bool) -> str:
    if budget_sensitive:
        return "돈을 내기 전에 최소 범위와 중도 해지 조건이 먼저 보여야 함"
    if low_digital:
        return "직접 다뤄야 하는 화면이 많으면 도입을 미룰 가능성이 큼"
    if high_digital:
        return "기존 도구보다 빠르다는 수치가 없으면 직접 만들거나 다른 SaaS를 비교할 가능성이 큼"
    if cautious:
        return "실패 사례와 책임 경계가 없으면 과장된 약속으로 받아들일 수 있음"
    if any(token in text for token in ["개인정보", "보안", "병원", "세무", "학원"]):
        return "데이터 처리 경계가 흐리면 내부 승인에서 막힐 수 있음"
    return "업무별 적용 범위가 흐리면 관심은 있어도 다음 행동으로 이어지기 어려움"


def _decision_frame(*, low_digital: bool, high_digital: bool, cautious: bool, budget_sensitive: bool) -> str:
    if budget_sensitive:
        return "월 비용, 해지 조건, 최소 도입 범위를 먼저 비교한 뒤 결정"
    if low_digital:
        return "내가 직접 배울 분량과 지원 방식을 본 뒤 결정"
    if high_digital:
        return "기존 도구와 효과 수치를 비교한 뒤 빠르게 실험"
    if cautious:
        return "한계, 책임 범위, 실패 대응을 확인한 뒤 결정"
    return "업무 절감 효과와 도입 조건을 비교한 뒤 결정"


def _audience_label(profile: PersonaProfile) -> str:
    summary = " ".join(profile.summary.split())
    if not summary:
        return profile.segment
    return summary.split(".")[0]
