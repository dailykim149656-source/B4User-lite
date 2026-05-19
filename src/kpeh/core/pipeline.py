from __future__ import annotations

from pathlib import Path
from typing import Any

from kpeh.core.io_utils import read_jsonl, write_json, write_jsonl
from kpeh.core.models import EvaluationResult, EvaluationScenario, PersonaProfile, ServiceSpec, SyntheticUserQuestion
from kpeh.core.persona_compiler import compile_personas
from kpeh.core.persona_loader import load_personas, load_service_spec
from kpeh.core.persona_sampler import sample_personas
from kpeh.core.question_generator import generate_questions
from kpeh.core.report_generator import generate_report, write_report
from kpeh.core.response_collector import collect_responses
from kpeh.core.rubric_evaluator import evaluate_responses
from kpeh.core.rubric_loader import load_failure_modes, load_rubric
from kpeh.core.scenario_generator import generate_scenarios


def generate_question_set(
    personas_path: str | Path,
    service_path: str | Path,
    domain_pack: str | Path | None,
    n_personas: int,
    questions_per_persona: int,
    output: str | Path,
    seed: int | None = None,
    filters: dict[str, Any] | None = None,
    sampling_strategy: str | Path | dict[str, Any] | None = "random",
) -> tuple[list[PersonaProfile], list[EvaluationScenario], list[SyntheticUserQuestion], ServiceSpec, list[str]]:
    personas = load_personas(personas_path)
    service = load_service_spec(service_path)
    sample = sample_personas(personas, n_personas, filters=filters, seed=seed, sampling_strategy=sampling_strategy)
    profiles = compile_personas(sample.records)
    scenarios = generate_scenarios(profiles, service)
    questions = generate_questions(scenarios, profiles, service, questions_per_scenario=questions_per_persona, seed=seed)
    output_path = Path(output)
    write_jsonl(output_path.parent / "profiles.jsonl", profiles)
    write_jsonl(output_path.parent / "scenarios.jsonl", scenarios)
    write_jsonl(output_path, questions)
    return profiles, scenarios, questions, service, list(sample.warnings)


def evaluate_question_responses(
    questions_path: str | Path,
    responses_path: str | Path | None,
    rubric_source: str | Path | None,
    failure_modes_source: str | Path | None,
    output: str | Path,
    mock_missing: bool = False,
) -> list[EvaluationResult]:
    questions = [SyntheticUserQuestion.from_dict(row) for row in read_jsonl(questions_path)]
    responses = collect_responses(questions, responses_path, mock_missing=mock_missing)
    results = evaluate_responses(responses, questions, load_rubric(rubric_source), load_failure_modes(failure_modes_source))
    write_jsonl(output, results)
    return results


def generate_markdown_report(
    results_path: str | Path,
    profiles_path: str | Path,
    scenarios_path: str | Path,
    questions_path: str | Path,
    output: str | Path,
    service_path: str | Path | None = None,
) -> str:
    results = [EvaluationResult.from_dict(row) for row in read_jsonl(results_path)]
    profiles = [PersonaProfile.from_dict(row) for row in read_jsonl(profiles_path)]
    scenarios = [EvaluationScenario.from_dict(row) for row in read_jsonl(scenarios_path)]
    questions = [SyntheticUserQuestion.from_dict(row) for row in read_jsonl(questions_path)]
    service = load_service_spec(service_path) if service_path else None
    content = generate_report(results, profiles, scenarios, questions, service=service)
    write_report(output, content)
    return content


def run_pipeline(
    personas_path: str | Path,
    service_path: str | Path,
    domain_pack: str | Path | None,
    n_personas: int,
    questions_per_persona: int,
    output_dir: str | Path,
    seed: int | None = None,
    responses_path: str | Path | None = None,
    filters: dict[str, Any] | None = None,
    sampling_strategy: str | Path | dict[str, Any] | None = "random",
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    questions_path = output_dir / "questions.jsonl"
    profiles, scenarios, questions, service, warnings = generate_question_set(
        personas_path=personas_path,
        service_path=service_path,
        domain_pack=domain_pack,
        n_personas=n_personas,
        questions_per_persona=questions_per_persona,
        output=questions_path,
        seed=seed,
        filters=filters,
        sampling_strategy=sampling_strategy,
    )
    responses = collect_responses(questions, responses_path, mock_missing=responses_path is None)
    target_responses_path = output_dir / "target_responses.jsonl"
    write_jsonl(target_responses_path, responses)
    results_path = output_dir / "evaluation_results.jsonl"
    results = evaluate_responses(
        responses,
        questions,
        load_rubric(_domain_file_or_generic(domain_pack, "rubrics.yaml")),
        load_failure_modes(_domain_file_or_generic(domain_pack, "failure_modes.yaml")),
    )
    write_jsonl(results_path, results)
    report_path = output_dir / "report.md"
    write_report(report_path, generate_report(results, profiles, scenarios, questions, service=service))
    run_config_path = output_dir / "run_config.json"
    write_json(
        run_config_path,
        {
            "tool": "b4user-lite",
            "evaluation_mode": "response_quality",
            "personas_path": str(personas_path),
            "service_path": str(service_path),
            "domain_pack": str(domain_pack or "generic"),
            "n_personas": n_personas,
            "questions_per_persona": questions_per_persona,
            "seed": seed,
            "warnings": warnings,
            "synthetic_hypothesis_warning": "Synthetic persona results are hypotheses and do not replace real user research.",
        },
    )
    return {
        "profiles": output_dir / "profiles.jsonl",
        "scenarios": output_dir / "scenarios.jsonl",
        "questions": questions_path,
        "target_responses": target_responses_path,
        "evaluation_results": results_path,
        "report": report_path,
        "run_config": run_config_path,
    }


def _domain_file_or_generic(domain_pack: str | Path | None, filename: str) -> str | Path | None:
    if domain_pack is None or str(domain_pack) == "generic":
        return "generic"
    path = Path(domain_pack)
    if path.is_dir():
        return path / filename
    return domain_pack
