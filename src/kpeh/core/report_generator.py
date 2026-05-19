from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from kpeh.core.io_utils import ensure_parent_dir
from kpeh.core.models import EvaluationResult, EvaluationScenario, PersonaProfile, ServiceSpec, SyntheticUserQuestion


def generate_report(
    results: list[EvaluationResult],
    profiles: list[PersonaProfile],
    scenarios: list[EvaluationScenario],
    questions: list[SyntheticUserQuestion],
    service: ServiceSpec | None = None,
) -> str:
    completed = [result for result in results if result.status == "completed" and result.max_score > 0]
    question_by_id = {question.question_id: question for question in questions}
    overall_average = _overall_average(completed)
    criterion_average = _criterion_average(completed)
    failure_counts = Counter(code for result in results for code in result.failure_modes)
    segment_counts = Counter(profile.segment for profile in profiles)

    lines: list[str] = []
    lines.append("# B4User Evaluation Report")
    lines.append("")
    lines.append(
        "> 본 리포트는 합성 페르소나 기반 평가 결과입니다. 실제 사용자 조사나 시장 반응 예측을 대체하지 않으며, 제품 개선을 위한 가설로 사용해야 합니다."
    )
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- 평가 질문 수: {len(questions)}")
    lines.append(f"- 수집 응답 수: {len([result for result in results if result.status == 'completed'])}")
    lines.append(f"- skipped 응답 수: {len([result for result in results if result.status != 'completed'])}")
    lines.append(f"- 전체 평균 점수: {overall_average:.2f}")
    lines.append("")
    lines.append("## 평가 대상 서비스")
    lines.append("")
    if service:
        lines.append(f"- 이름: {service.name}")
        lines.append(f"- 설명: {service.description}")
        if service.known_limits:
            lines.append(f"- 알려진 한계: {', '.join(service.known_limits)}")
    else:
        lines.append("- 서비스 정보가 report 명령에 제공되지 않았습니다.")
    lines.append("")
    lines.append("## 테스트한 Synthetic User 세그먼트")
    lines.append("")
    for segment, count in segment_counts.most_common():
        lines.append(f"- {segment}: {count}명")
    lines.append("")
    lines.append("## Persona별 질문/평가 신호")
    lines.append("")
    observation_rows = _persona_observation_rows(results, profiles, questions)
    if observation_rows:
        for row in observation_rows:
            lines.append(f"- {row['segment']} / {row['summary']}")
            lines.append(f"  - 질문: {row['question']}")
            lines.append(f"  - 점수: {row['score']}")
            if row["concerns"]:
                lines.append(f"  - 주요 우려: {row['concerns']}")
            if row["signal"]:
                lines.append(f"  - 개선 신호: {row['signal']}")
    else:
        lines.append("- persona별로 연결된 평가 결과가 없습니다.")
    lines.append("")
    lines.append("## Criterion별 평균 점수")
    lines.append("")
    for criterion, average in criterion_average.items():
        lines.append(f"- {criterion}: {average:.2f}")
    lines.append("")
    lines.append("## 주요 실패 유형")
    lines.append("")
    if failure_counts:
        for code, count in failure_counts.most_common(5):
            label = _label_for_code(code, results)
            lines.append(f"- {label} (`{code}`): {count}건")
    else:
        lines.append("- 감지된 주요 실패 유형이 없습니다.")
    lines.append("")
    lines.append("## 대표 실패 사례")
    lines.append("")
    failed_results = [result for result in results if result.failure_modes]
    for result in sorted(failed_results, key=lambda item: item.total_score)[:3]:
        question = question_by_id.get(result.question_id)
        lines.append(f"- 질문: {question.question if question else result.question_id}")
        lines.append(f"  - 점수: {result.total_score}/{result.max_score}, 실패 유형: {', '.join(result.failure_modes)}")
    if not failed_results:
        lines.append("- 감지된 대표 실패 사례가 없습니다.")
    lines.append("")
    lines.append("## 좋은 응답 사례")
    lines.append("")
    for result in sorted(completed, key=lambda item: item.total_score, reverse=True)[:3]:
        question = question_by_id.get(result.question_id)
        lines.append(f"- 질문: {question.question if question else result.question_id}")
        lines.append(f"  - 점수: {result.total_score}/{result.max_score}")
    lines.append("")
    lines.append("## 개선 우선순위")
    lines.append("")
    for suggestion, count in _suggestion_counts(results).most_common(5):
        lines.append(f"- {suggestion} ({count}건)")
    lines.append("")
    lines.append("## 다음 평가 제안")
    lines.append("")
    lines.append("- 점수가 낮은 failure mode에 맞춰 대상 AI 응답 프롬프트나 정책 문구를 수정한 뒤 같은 질문 세트로 재평가합니다.")
    lines.append("- 도메인팩을 추가할 때는 core 코드를 바꾸지 말고 루브릭과 failure mode 정의를 확장합니다.")
    lines.append("- skipped 응답이 있다면 응답 수집을 완료한 뒤 리포트를 다시 생성합니다.")
    lines.append("")
    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    ensure_parent_dir(path)
    Path(path).write_text(content, encoding="utf-8", newline="\n")


def _overall_average(results: list[EvaluationResult]) -> float:
    if not results:
        return 0.0
    ratios = [result.total_score / result.max_score * 100 for result in results if result.max_score > 0]
    return sum(ratios) / len(ratios) if ratios else 0.0


def _criterion_average(results: list[EvaluationResult]) -> dict[str, float]:
    values: dict[str, list[int]] = defaultdict(list)
    for result in results:
        for criterion, score in result.scores.items():
            values[criterion].append(score)
    return {criterion: sum(scores) / len(scores) for criterion, scores in values.items()}


def _suggestion_counts(results: list[EvaluationResult]) -> Counter[str]:
    return Counter(suggestion for result in results for suggestion in result.improvement_suggestions)


def _persona_observation_rows(
    results: list[EvaluationResult],
    profiles: list[PersonaProfile],
    questions: list[SyntheticUserQuestion],
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    question_by_id = {question.question_id: question for question in questions}
    profile_by_id = {profile.profile_id: profile for profile in profiles}
    rows: list[dict[str, str]] = []
    seen_profiles: set[str] = set()
    ordered = sorted(results, key=lambda result: (_score_ratio(result), result.question_id))
    for result in ordered:
        question = question_by_id.get(result.question_id)
        if question is None or question.profile_id in seen_profiles:
            continue
        profile = profile_by_id.get(question.profile_id)
        if profile is None:
            continue
        seen_profiles.add(question.profile_id)
        rows.append(
            {
                "segment": profile.segment,
                "summary": _compact_text(profile.summary, 120),
                "question": _compact_text(question.question, 180),
                "score": f"{result.total_score}/{result.max_score}",
                "concerns": ", ".join(concern.name for concern in profile.likely_concerns[:3]),
                "signal": _compact_text(_first_signal(result), 160),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _score_ratio(result: EvaluationResult) -> float:
    return result.total_score / result.max_score if result.max_score else 1.0


def _first_signal(result: EvaluationResult) -> str:
    if result.improvement_suggestions:
        return result.improvement_suggestions[0]
    if result.failure_modes:
        return ", ".join(result.failure_modes[:3])
    return "현재 응답은 이 persona의 질문에는 큰 실패 신호가 적었습니다."


def _compact_text(text: str, max_chars: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _label_for_code(code: str, results: list[EvaluationResult]) -> str:
    for result in results:
        for detail in result.failure_mode_details:
            if detail.get("code") == code:
                return str(detail.get("label_ko") or code)
    return code
