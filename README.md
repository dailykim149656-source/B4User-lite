# B4User-lite

B4User-lite is an Apache-2.0, offline-first pre-user validation harness for testing agent or product responses against Korean synthetic personas before real deployment.

> Synthetic users are not real users. B4User-lite outputs are synthetic persona evaluation hypotheses. They do not replace real user research, market demand validation, employee interviews, or production safety review.

## What Is Public Here

- `b4user` CLI for JSONL persona input and YAML/JSON service config.
- Deterministic question generation, mock response collection, basic response-quality evaluation, and Markdown/JSONL artifacts.
- Nemotron-Personas-Korea import support with source attribution metadata.
- Generic illustrative rubric axes such as clarity, actionability, risk disclosure, and persona fit.

The private B4User working repository is not public. Advanced rubrics, AX adoption-friction scoring, industry domain packs, Product Risk Profile, evaluator training, ontology/promotion bridges, Sales Pack logic, generated artifacts, private docs, and raw/processed datasets are intentionally excluded.

## Install For Development

```powershell
python -m pip install -e ".[dev]"
python -m b4user --help
```

Optional Nemotron/Hugging Face import support:

```powershell
python -m pip install -e ".[dev,hf]"
```

## Quick Smoke

```powershell
b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42
```

Generated artifacts are written under `outputs/`, which is ignored by Git.

## Nemotron Attribution

The importer targets `nvidia/Nemotron-Personas-Korea`, a separate NVIDIA dataset published under CC BY 4.0. Converted records preserve `metadata.source_dataset` and `metadata.source_license`.

## Public Export Audit

Before publishing a modified export, run:

```powershell
python scripts/audit_b4user_lite_export.py .
python -m pytest
```
