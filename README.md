<p align="center">
  <img src="assets/b4user-logo.png" alt="B4User-lite logo" width="640">
</p>

<p align="center"><strong>Build before users. But validate before users, too.</strong></p>

# B4User-lite

[한국어 README](README.ko.md)

B4User-lite is an Apache-2.0, offline-first pre-user validation harness for
testing whether an agent, product concept, or response pattern holds up against
Korean synthetic personas before real deployment.

It is not another persona survey tool. It is a small, repeatable harness for
asking synthetic users structured questions, collecting target responses,
scoring those responses with an illustrative baseline rubric, and producing
evidence artifacts that a human can review.

> Synthetic users are not real users. B4User-lite outputs are synthetic persona
> evaluation hypotheses. They do not replace real user research, market demand
> validation, employee interviews, legal review, security review, or production
> safety approval.

## What You Can Do With It

- Generate Korean synthetic-user questions from JSONL personas and a YAML
  service spec.
- Run a deterministic local evaluation with mock target responses.
- Evaluate collected target responses against a generic response-quality rubric.
- Produce Markdown reports, persona-selection audits, and JSONL artifacts for review.
- Attach directional market-evidence CSV/JSON signals to report claim limits.
- Import a sample from `nvidia/Nemotron-Personas-Korea` when the optional
  Hugging Face dependencies are installed.

## What Is Included

- `b4user` CLI for the lite workflow.
- JSONL persona loading and YAML/JSON service config loading.
- Deterministic persona sampling, persona compilation, scenario generation, and
  question generation.
- Mock response collection for offline smoke tests.
- Basic response-quality scoring with generic rubric axes:
  `clarity`, `actionability`, `risk_disclosure`, and `persona_fit`.
- Markdown report generation with Decision Brief, claim ledger, and explicit
  synthetic-hypothesis wording.
- Persona-selection audit output that shows sampling logic, target-fit caveats,
  and human review candidates.
- Nemotron-Personas-Korea importer with source attribution metadata.
- npm wrapper package source for installing/running the Python CLI.

## Install For Development

Requirements:

- Python 3.11+
- Node.js 18+ only if you want to inspect or package the npm wrapper

```powershell
python -m pip install -e ".[dev]"
python -m b4user --help
```

Optional Nemotron/Hugging Face import support:

```powershell
python -m pip install -e ".[dev,hf]"
```

## Quick Start

Run the deterministic local demo:

```powershell
b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42
```

Generated artifacts are written under `outputs/`, which is ignored by Git.

Typical outputs:

- `profiles.jsonl`: compiled synthetic-user profiles
- `scenarios.jsonl`: evaluation situations for each profile
- `questions.jsonl`: generated synthetic-user questions
- `target_responses.jsonl`: provided or mock target responses
- `evaluation_results.jsonl`: rubric scores and failure signals
- `persona_selection_audit.json`: sampling logic and target-fit caveats
- `persona_selection_report.md`: human-readable persona panel review notes
- `report.md`: human-readable synthetic-evidence report
- `run_config.json`: run metadata with the synthetic-hypothesis warning

To attach directional market evidence from sources such as keyword research,
Search Console exports, or landing-page conversion logs, pass a CSV or JSON file:

```powershell
b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42 --market-evidence market_evidence.csv
```

Market evidence changes the report's claim limits; it does not turn synthetic
persona scores into real market validation.

## CLI Commands

Generate questions only:

```powershell
b4user generate-questions --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 10 --questions-per-persona 2 --output outputs/questions.jsonl --seed 42
```

Evaluate existing responses:

```powershell
b4user evaluate --questions outputs/questions.jsonl --responses data/responses_sample.jsonl --rubric generic --failure-modes generic --output outputs/evaluation_results.jsonl
```

Generate a Markdown report:

```powershell
b4user report --results outputs/evaluation_results.jsonl --profiles outputs/profiles.jsonl --scenarios outputs/scenarios.jsonl --questions outputs/questions.jsonl --service configs/service.yaml --output outputs/report.md
```

Add `--market-evidence market_evidence.csv` to include directional external
signals in the regenerated report.

Import Nemotron personas:

```powershell
b4user import-nemotron --n 100 --seed 42 --output data/processed/nemotron_sample.jsonl
```

`data/processed/` is ignored by Git. Do not commit imported dataset rows unless
you have reviewed the license, attribution, and privacy implications for your
use case.

## Input Formats

Personas are JSONL records with fields like:

```json
{"persona_id":"kr_000001","age":47,"gender":"female","province":"전라북도","city":"전주시","occupation":"제조업 사무직","digital_literacy":"medium","persona":"반복적인 엑셀 정리 업무를 줄이고 싶지만 비용과 유지보수 조건을 확인하고 싶어한다."}
```

The service spec is YAML:

```yaml
name: Example Agent
description: Helps small teams automate repetitive customer follow-up.
target_users:
  - Small business operators
service_capabilities:
  - Draft follow-up messages
  - Explain automation limits
known_limits:
  - Requires human review before sending messages
```

## Nemotron Attribution

The importer targets `nvidia/Nemotron-Personas-Korea`, a separate NVIDIA dataset
published under CC BY 4.0. Converted records preserve attribution through:

- `metadata.source_dataset`
- `metadata.source_license`
- `metadata.source_fields`

## License

B4User-lite is licensed under Apache-2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
