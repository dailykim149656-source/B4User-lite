from __future__ import annotations

from pathlib import Path

from kpeh.core.io_utils import read_jsonl
from kpeh.core.models import SyntheticUserQuestion, TargetResponse
from kpeh.llm.base import TextGenerator


def load_target_responses(path: str | Path) -> list[TargetResponse]:
    return [TargetResponse.from_dict(row) for row in read_jsonl(path)]


def collect_responses(
    questions: list[SyntheticUserQuestion],
    responses_path: str | Path | None = None,
    mock_missing: bool = False,
    target_generator: TextGenerator | None = None,
    target_name: str = "target_agent",
    target_system_prompt: str | None = None,
    target_strict: bool = False,
    warnings: list[str] | None = None,
) -> list[TargetResponse]:
    responses_by_question: dict[str, TargetResponse] = {}
    if responses_path:
        for response in load_target_responses(responses_path):
            responses_by_question[response.question_id] = response

    collected: list[TargetResponse] = []
    for question in questions:
        response = responses_by_question.get(question.question_id)
        if response is not None:
            collected.append(response)
        elif target_generator is not None:
            collected.append(
                collect_llm_response(
                    question,
                    target_generator=target_generator,
                    target_name=target_name,
                    target_system_prompt=target_system_prompt,
                    target_strict=target_strict,
                    warnings=warnings,
                )
            )
        elif mock_missing:
            collected.append(mock_response(question))
        else:
            collected.append(
                TargetResponse(
                    response_id=f"resp_{question.question_id}",
                    question_id=question.question_id,
                    model_or_service="missing_response",
                    response_text="",
                    status="skipped",
                )
            )
    return collected


def collect_llm_response(
    question: SyntheticUserQuestion,
    *,
    target_generator: TextGenerator,
    target_name: str,
    target_system_prompt: str | None = None,
    target_strict: bool = False,
    warnings: list[str] | None = None,
) -> TargetResponse:
    prompt = _target_prompt(question, target_system_prompt)
    try:
        response_text = target_generator.generate(prompt).strip()
    except Exception as exc:
        message = f"target agent response failed for {question.question_id}: {exc}"
        if warnings is not None:
            warnings.append(message)
        if target_strict:
            raise RuntimeError(message) from exc
        return TargetResponse(
            response_id=f"resp_{question.question_id}",
            question_id=question.question_id,
            model_or_service=target_name,
            response_text="",
            metadata={"source": "target_agent", "error": str(exc)},
            status="skipped",
        )

    if not response_text:
        message = f"target agent returned an empty response for {question.question_id}"
        if warnings is not None:
            warnings.append(message)
        if target_strict:
            raise RuntimeError(message)
        return TargetResponse(
            response_id=f"resp_{question.question_id}",
            question_id=question.question_id,
            model_or_service=target_name,
            response_text="",
            metadata={"source": "target_agent", "error": "empty_response"},
            status="skipped",
        )

    return TargetResponse(
        response_id=f"resp_{question.question_id}",
        question_id=question.question_id,
        model_or_service=target_name,
        response_text=response_text,
        metadata={"source": "target_agent"},
    )


def mock_response(question: SyntheticUserQuestion) -> TargetResponse:
    risk_phrase = _risk_phrase(question)
    text = (
        f"질문하신 내용은 도입 전에 반드시 확인해야 합니다. {risk_phrase} "
        "가능 여부와 업무 범위는 사용하는 자료 형식과 현재 프로세스에 따라 달라질 수 있습니다. "
        "무료로 가능한 범위와 별도 견적이 필요한 범위를 먼저 나누고, 개인정보가 포함된다면 처리 목적, "
        "보관 기간, 접근 권한, 삭제 절차를 문서로 확인하세요. "
        "다음 단계로는 현재 업무 예시 2~3개와 사용 중인 양식을 공유해 범위와 비용 조건을 확인하는 것이 좋습니다."
    )
    return TargetResponse(
        response_id=f"resp_{question.question_id}",
        question_id=question.question_id,
        model_or_service="mock_target",
        response_text=text,
        metadata={"source": "mock"},
    )


def _target_prompt(question: SyntheticUserQuestion, system_prompt: str | None) -> str:
    instructions = system_prompt or (
        "당신은 평가 대상 AI agent입니다. 사용자의 질문에 한국어로 직접 답하세요. "
        "가능 범위, 한계, 비용, 개인정보, 책임 소재가 관련되면 숨기지 말고 설명하세요."
    )
    return "\n\n".join(
        [
            instructions.strip(),
            "다음 사용자 질문에 답하세요.",
            f"질문: {question.question}",
        ]
    )


def _risk_phrase(question: SyntheticUserQuestion) -> str:
    if "maintenance" in question.risk_tags:
        return "양식 변경이나 유지보수는 계약 범위, 수정 횟수, 변경 규모에 따라 비용이 달라질 수 있습니다."
    if "privacy" in question.risk_tags:
        return "고객 개인정보를 다루는 경우 별도 동의, 접근 제한, 삭제 기준이 필요합니다."
    if "responsibility" in question.risk_tags:
        return "자동화 결과는 사람이 최종 검수해야 하며 책임 범위를 사전에 정해야 합니다."
    if "pricing_transparency" in question.risk_tags:
        return "초기 구축비, 월 유지비, 추가 작업 비용을 분리해 확인해야 합니다."
    return "서비스의 가능 범위와 한계를 함께 확인해야 합니다."
