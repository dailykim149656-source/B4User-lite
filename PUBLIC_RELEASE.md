# B4User-lite Public Release Boundary

B4User-lite is the open distribution boundary for B4User. The private working
repository remains private; public release work must be done from a reviewed
clean export with fresh public history.

## Positioning

> B4User is not another persona survey tool. It is a pre-user validation
> harness that stress-tests whether an agent or product survives Korean
> synthetic users before real deployment.

The public release should plant the category flag: persona data is becoming
easy to access, so B4User-lite focuses on the repeatable harness around what to
ask, how to collect responses, and how to report synthetic evidence without
overstating it.

## Public Surface

Include only the pieces needed for a deterministic, auditable demo path:

- `b4user` CLI for JSONL persona input, YAML/JSON config, question generation,
  mock response collection, basic response evaluation, and Markdown/JSONL
  artifacts.
- Nemotron-Personas-Korea import example and source attribution metadata.
- Demo personas, demo responses, generic service/config examples, and generic
  illustrative rubric axes such as clarity, trust risk, adoption friction, and
  next-action usefulness.
- Root-level public docs: `README.md`, `PUBLIC_RELEASE.md`,
  `REPOSITORY_POLICY.md`, `LICENSE`, and `NOTICE`.
- Tests and scripts that prove the public export excludes private docs,
  generated artifacts, raw/processed datasets, credentials, and proprietary
  domain logic.

## Private Surface

Keep these out of public source, public packages, public examples, and public
release history:

- Advanced evaluation rubrics and report interpretation logic.
- AX adoption-friction scoring, trust-collapse signals, responsibility/cost/
  operations-risk question sets, and production-readiness gates.
- Industry domain packs beyond generic illustrative examples.
- Evaluator training, ML models, tuning data, risk profiles, ontology/promotion
  bridges, Sales Pack logic, and PM/marketing decision frameworks.
- Private planning docs, decks, PDFs, DOCX files, generated outputs, raw or
  processed datasets, local paths, credentials, API keys, bridge commands, and
  private repository URLs.

## License And Attribution

B4User-lite uses Apache-2.0 by default to maximize standard-setting and
business adoption. Do not switch to AGPL for the public release unless the
strategic goal changes from category adoption to SaaS wrapping prevention.

Nemotron-Personas-Korea is a separate NVIDIA dataset published under CC BY 4.0.
Any public example that imports or converts it must keep source attribution,
including the dataset id and license in generated metadata.

## Verification

Before creating or publishing a public repository:

1. Create a separate clean export directory; do not make this private working
   repository public.
2. Run `python scripts/audit_b4user_lite_export.py <clean-export-dir>`.
3. Run the package audits from `REPOSITORY_POLICY.md`.
4. Run the deterministic smoke path from the clean export:

   ```powershell
   python -m pip install -e ".[dev]"
   python -m pytest
   b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42
   ```

5. Inspect README and generated reports for synthetic-hypothesis wording. They
   must not describe synthetic scores as real user research, market demand
   forecasts, employee findings, or production safety approval.
