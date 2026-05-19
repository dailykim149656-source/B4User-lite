# Public Export Audit

This document is for maintainers preparing a modified B4User-lite public export.
It is intentionally separate from the user-facing README.

## Why This Exists

B4User-lite is the public, lightweight boundary of the B4User project. The README
should explain what users can do with the tool. This document records the
publication checks that keep the public export clean and reproducible.

## Public Boundary

The public export should include:

- the `b4user` CLI and deterministic lite workflow
- sample personas, sample responses, and sample service config
- the generic domain pack
- the Nemotron-Personas-Korea importer with source attribution metadata
- tests, packaging metadata, license, notice, and public documentation

The public export should not include:

- private planning notes or decks
- generated run outputs
- raw or processed dataset dumps
- local environment files or credentials
- proprietary domain packs
- advanced private evaluation, scoring, training, reporting, or sales logic

## Before Publishing A Modified Export

Run these checks from the export root:

```powershell
python scripts/audit_b4user_lite_export.py .
python -m pytest
```

The audit checks that the export keeps the lite boundary and preserves required
public release metadata. The test suite checks that the packaged CLI still runs
and that the lite pipeline can produce basic artifacts.

## Wording Check

Public-facing docs and reports should describe B4User-lite outputs as synthetic
evaluation hypotheses. They should not describe synthetic persona results as real
user research, demand forecasts, employee research findings, legal review,
security review, or production approval.

## Nemotron Attribution

Examples that use `nvidia/Nemotron-Personas-Korea` should retain the source
dataset name, license metadata, and CC BY 4.0 notice.
