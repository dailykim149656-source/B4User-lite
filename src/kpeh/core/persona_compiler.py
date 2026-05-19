from __future__ import annotations

from kpeh.core.models import LikelyConcern, PersonaProfile, PersonaRecord


DEFAULT_EVALUATION_FOCUS = ["clarity", "actionability", "risk_disclosure", "persona_fit"]


def compile_persona(record: PersonaRecord, index: int) -> PersonaProfile:
    source_fields = _source_fields(record)
    segment = _segment(record)
    concerns = _concerns(record)
    return PersonaProfile(
        profile_id=f"profile_{index:03d}",
        persona_id=record.persona_id,
        segment=segment,
        summary=_summary(record),
        communication_style=_communication_style(record),
        likely_concerns=concerns,
        evaluation_focus=list(DEFAULT_EVALUATION_FOCUS),
        metadata={"source_fields": {key: value for key, value in source_fields.items() if value is not None}},
    )


def compile_personas(records: list[PersonaRecord]) -> list[PersonaProfile]:
    return [compile_persona(record, index) for index, record in enumerate(records, start=1)]


def _summary(record: PersonaRecord) -> str:
    location = " ".join(item for item in [record.province, record.city] if item)
    age = f"{record.age}세" if record.age is not None else "연령 미상"
    occupation = record.occupation or record.industry or "직업 미상"
    literacy = _digital_literacy_ko(record.digital_literacy)
    attitude = _attitude_ko(record.technology_attitude)
    prefix = f"{location} 거주 " if location else ""
    return f"{prefix}{age} {occupation}. {literacy}이며 {attitude}."


def _communication_style(record: PersonaRecord) -> str:
    if (record.digital_literacy or "").lower() in {"low", "medium_low", "낮음"}:
        return "전문 용어를 줄이고 단계별로 설명하는 방식을 선호"
    if (record.technology_attitude or "").lower() in {"cautious", "skeptical", "보수적"}:
        return "장점보다 한계와 조건을 먼저 확인할 수 있는 설명 선호"
    return "구체적이고 실용적인 설명 선호"


def _concerns(record: PersonaRecord) -> list[LikelyConcern]:
    concerns: list[LikelyConcern] = []
    occupation = (record.occupation or "").lower()
    industry = (record.industry or "").lower()
    digital_literacy = (record.digital_literacy or "").lower()
    income_band = (record.income_band or "").lower()
    attitude = (record.technology_attitude or "").lower()
    metadata_text = _metadata_text(record)

    concerns.append(
        LikelyConcern(
            name="비용 명확성",
            confidence=0.66,
            basis=_basis(record, ["income_band", "occupation", "persona", "professional_persona", "skills_and_expertise"]),
        )
    )
    if any(token in occupation for token in ["자영", "소상공", "사업", "사장", "카페", "식당", "철물", "미용"]) or "small" in industry:
        concerns.append(
            LikelyConcern(
                name="유지보수 부담",
                confidence=0.64,
                basis=_basis(record, ["occupation", "industry", "skills_and_expertise", "professional_persona"]),
            )
        )
    if any(token in metadata_text for token in ["장부", "문서", "정리", "행정", "예약", "문자", "보고", "반복"]):
        concerns.append(
            LikelyConcern(
                name="업무 자동화 적합성",
                confidence=0.63,
                basis=_basis(record, ["skills_and_expertise", "professional_persona", "career_goals_and_ambitions"]),
            )
        )
    if digital_literacy in {"low", "medium_low", "낮음"}:
        concerns.append(
            LikelyConcern(
                name="디지털 도구 학습 지연",
                confidence=0.7,
                basis=_basis(record, ["digital_literacy"]),
            )
        )
    if income_band in {"low", "lower", "낮음"}:
        concerns.append(
            LikelyConcern(
                name="월 비용 부담",
                confidence=0.62,
                basis=_basis(record, ["income_band"]),
            )
        )
    if attitude in {"cautious", "skeptical", "보수적", "pragmatic"}:
        concerns.append(
            LikelyConcern(
                name="도입 리스크",
                confidence=0.6,
                basis=_basis(record, ["technology_attitude"]),
            )
        )
    if not any(item.name == "개인정보 처리 우려" for item in concerns):
        concerns.append(
            LikelyConcern(
                name="개인정보 처리 우려",
                confidence=0.56,
                basis=_basis(record, ["persona", "occupation", "professional_persona", "cultural_background"]),
            )
        )
    if len(concerns) >= 2:
        return concerns[:4]
    return concerns + [LikelyConcern(name="다음 행동 안내 필요", confidence=0.55, basis=_basis(record, ["persona"]))]


def _segment(record: PersonaRecord) -> str:
    age_group = "unknown_age"
    if record.age is not None:
        if record.age < 30:
            age_group = "young"
        elif record.age < 50:
            age_group = "middle_aged"
        else:
            age_group = "older"
    occupation = (record.occupation or record.industry or "general_user").lower()
    if any(token in occupation for token in ["제조", "생산", "공장", "manufacturing"]):
        role = "manufacturing_worker"
    elif any(token in occupation for token in ["자영", "소상공", "사업", "사장", "카페", "식당", "철물", "미용"]):
        role = "small_business_owner"
    elif any(token in occupation for token in ["사무", "행정", "총무", "관리", "office"]):
        role = "office_worker"
    else:
        role = "general_user"
    return f"{age_group}_{role}"


def _basis(record: PersonaRecord, fields: list[str]) -> list[str]:
    source_fields = _source_fields(record)
    result: list[str] = []
    for field in fields:
        if getattr(record, field, None) not in {None, ""} or source_fields.get(field) not in {None, ""}:
            result.append(field)
    return result


def _source_fields(record: PersonaRecord) -> dict[str, object]:
    source_fields: dict[str, object] = {
        "age": record.age,
        "occupation": record.occupation,
        "industry": record.industry,
        "income_band": record.income_band,
        "digital_literacy": record.digital_literacy,
        "technology_attitude": record.technology_attitude,
        "province": record.province,
        "city": record.city,
        "persona": record.persona,
    }
    metadata_source_fields = record.metadata.get("source_fields")
    if isinstance(metadata_source_fields, dict):
        source_fields.update(metadata_source_fields)
    for key in ["source_dataset", "source_license"]:
        if key in record.metadata:
            source_fields[key] = record.metadata[key]
    return {key: value for key, value in source_fields.items() if _present(value)}


def _metadata_text(record: PersonaRecord) -> str:
    source_fields = _source_fields(record)
    text_parts: list[str] = []
    for value in source_fields.values():
        if isinstance(value, list):
            text_parts.extend(str(item) for item in value)
        else:
            text_parts.append(str(value))
    return " ".join(text_parts).lower()


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value == "":
        return False
    return True


def _digital_literacy_ko(value: str | None) -> str:
    mapping = {
        "low": "디지털 도구 사용에 익숙하지 않은 편",
        "medium_low": "디지털 도구 사용에 다소 부담을 느끼는 편",
        "medium": "보통 수준의 디지털 숙련도",
        "high": "디지털 도구에 익숙한 편",
    }
    return mapping.get((value or "").lower(), "디지털 숙련도 정보가 제한적")


def _attitude_ko(value: str | None) -> str:
    mapping = {
        "pragmatic": "실용적인 근거를 중시함",
        "cautious": "도입 전 리스크 확인을 중시함",
        "skeptical": "과장된 설명을 경계함",
        "enthusiastic": "새 도구 수용에 적극적임",
    }
    return mapping.get((value or "").lower(), "서비스 설명의 구체성을 중시함")
