from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from kpeh import __version__
from kpeh.core.pipeline import evaluate_question_responses, generate_markdown_report, generate_question_set, run_pipeline
from kpeh.data_sources.nemotron_korea import import_nemotron_personas


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="b4user", description="B4User-lite synthetic persona validation harness")
    parser.add_argument("--version", action="version", version=f"b4user {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate-questions", help="Generate synthetic-user questions")
    generate.add_argument("--personas", required=True)
    generate.add_argument("--service", required=True)
    generate.add_argument("--domain-pack", default="generic")
    generate.add_argument("--n-personas", type=int, default=30)
    generate.add_argument("--questions-per-persona", type=int, default=2)
    generate.add_argument("--output", required=True)
    generate.add_argument("--seed", type=int)
    generate.add_argument("--filters", help="JSON object of persona filters")
    generate.add_argument("--sampling-strategy", default="random")
    generate.set_defaults(func=_generate_questions)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate responses with the generic rubric")
    evaluate.add_argument("--questions", required=True)
    evaluate.add_argument("--responses")
    evaluate.add_argument("--rubric", default="generic")
    evaluate.add_argument("--failure-modes", default="generic")
    evaluate.add_argument("--output", required=True)
    evaluate.add_argument("--mock-missing", action="store_true")
    evaluate.set_defaults(func=_evaluate)

    report = subparsers.add_parser("report", help="Generate a Markdown report")
    report.add_argument("--results", required=True)
    report.add_argument("--profiles", required=True)
    report.add_argument("--scenarios", required=True)
    report.add_argument("--questions", required=True)
    report.add_argument("--service")
    report.add_argument("--output", required=True)
    report.set_defaults(func=_report)

    run = subparsers.add_parser("run", help="Run the deterministic lite pipeline")
    run.add_argument("--personas", required=True)
    run.add_argument("--service", required=True)
    run.add_argument("--domain-pack", default="generic")
    run.add_argument("--n-personas", type=int, default=30)
    run.add_argument("--questions-per-persona", type=int, default=2)
    run.add_argument("--responses")
    run.add_argument("--output-dir", required=True)
    run.add_argument("--seed", type=int)
    run.add_argument("--filters", help="JSON object of persona filters")
    run.add_argument("--sampling-strategy", default="random")
    run.set_defaults(func=_run)

    importer = subparsers.add_parser("import-nemotron", help="Import nvidia/Nemotron-Personas-Korea personas")
    importer.add_argument("--output", required=True)
    importer.add_argument("--dataset", default="nvidia/Nemotron-Personas-Korea")
    importer.add_argument("--split", default="train")
    importer.add_argument("--n", type=int, default=5000)
    importer.add_argument("--seed", type=int, default=42)
    importer.add_argument("--max-source-rows", type=int)
    streaming = importer.add_mutually_exclusive_group()
    streaming.add_argument("--streaming", dest="streaming", action="store_true", default=True)
    streaming.add_argument("--no-streaming", dest="streaming", action="store_false")
    importer.set_defaults(func=_import_nemotron)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args) or 0)


def _json_filters(raw: str | None) -> dict[str, object] | None:
    if not raw:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("--filters must be a JSON object")
    return value


def _generate_questions(args: argparse.Namespace) -> int:
    profiles, scenarios, questions, _service, warnings = generate_question_set(
        args.personas,
        args.service,
        args.domain_pack,
        args.n_personas,
        args.questions_per_persona,
        args.output,
        seed=args.seed,
        filters=_json_filters(args.filters),
        sampling_strategy=args.sampling_strategy,
    )
    output = Path(args.output)
    print(f"profiles={output.parent / 'profiles.jsonl'}")
    print(f"scenarios={output.parent / 'scenarios.jsonl'}")
    print(f"questions={output}")
    print(f"count={len(questions)}")
    for warning in warnings:
        print(f"warning={warning}")
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    results = evaluate_question_responses(args.questions, args.responses, args.rubric, args.failure_modes, args.output, mock_missing=args.mock_missing)
    print(f"evaluation_results={Path(args.output)}")
    print(f"count={len(results)}")
    return 0


def _report(args: argparse.Namespace) -> int:
    generate_markdown_report(args.results, args.profiles, args.scenarios, args.questions, args.output, service_path=args.service)
    print(f"report={Path(args.output)}")
    return 0


def _run(args: argparse.Namespace) -> int:
    outputs = run_pipeline(
        args.personas,
        args.service,
        args.domain_pack,
        args.n_personas,
        args.questions_per_persona,
        args.output_dir,
        seed=args.seed,
        responses_path=args.responses,
        filters=_json_filters(args.filters),
        sampling_strategy=args.sampling_strategy,
    )
    for key, path in outputs.items():
        print(f"{key}={path}")
    return 0


def _import_nemotron(args: argparse.Namespace) -> int:
    summary = import_nemotron_personas(
        output=args.output,
        dataset=args.dataset,
        split=args.split,
        n=args.n,
        seed=args.seed,
        max_source_rows=args.max_source_rows,
        streaming=args.streaming,
    )
    print(
        " ".join(
            [
                f"dataset={summary.dataset}",
                f"split={summary.split}",
                f"converted={summary.converted_count}",
                f"scanned={summary.source_rows_scanned}",
                f"output={summary.output}",
                f"summary={summary.summary_output}",
            ]
        )
    )
    return 0
