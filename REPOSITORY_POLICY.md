# Repository and Publication Policy

This repository is the private working repository for B4User development. The internal Python implementation namespace remains `kpeh` for compatibility. Do **not** convert this repository to public. If a public repository is needed, create a separate clean repository from a reviewed export.

## Current repository roles

| Repository | Visibility | Purpose | Rule |
| --- | --- | --- | --- |
| `dailykim149656-source/B4User` | Private | Internal development, experiments, CI, private planning history | Keep private |
| Future public repository | Public | Installable/open distribution source | Create separately from a clean export |

## What belongs in this private repo

Track source and distribution-critical files:

- Python package source under `src/`
- CLI/package metadata such as `pyproject.toml`
- npm wrapper source under `npm/b4user-cli/`
- frontend source under `frontend/`
- tests and fixtures required for CI
- public-facing `README.md`
- CI workflows under `.github/workflows/`
- this policy document

Keep local/private files untracked:

- private planning docs
- product/positioning drafts
- presentation files
- PDFs, DOCX, PPTX, spreadsheets, Keynote files
- generated outputs and evaluation run artifacts
- raw/processed data
- local environment files and credentials

## `.gitignore` policy

The repository intentionally ignores private docs and presentation artifacts:

```gitignore
docs/
PT/
PRD.md
*.ppt
*.pptx
*.pdf
*.doc
*.docx
*.xls
*.xlsx
*.key
```

It also ignores runtime/generated directories such as:

```gitignore
outputs/
data/raw/
data/processed/
node_modules/
build/
dist/
```

If a documentation file must be public and tracked, put it at the repository root with an explicitly public name, for example:

```text
README.md
REPOSITORY_POLICY.md
PUBLIC_API.md
```

Do not put public docs under `docs/` unless `.gitignore` is deliberately changed.

## Important Git history warning

Removing a file from the latest commit does **not** remove it from Git history.

This private repository previously tracked some documents and presentation artifacts. They have been removed from the current `main` HEAD, but may still exist in older commits.

Therefore:

- Do not make this private repository public.
- Do not fork it into a public repository as-is.
- Do not use this repository's full history as a public source release.

If sensitive material must be removed from history, use a history rewrite tool such as `git filter-repo`, then force-push only after confirming the consequences.

## Public repository strategy

When a public repository is needed, create it separately from a clean working-tree export.

B4User-lite is the default public boundary. Its goal is to publish the
deterministic pre-user validation harness, not the private evaluation strategy.

Public B4User-lite exports may include:

- `b4user` CLI paths for JSONL persona input, YAML/JSON config, generic question
  generation, mock response collection, basic response-quality evaluation, and
  Markdown/JSONL artifacts.
- Nemotron-Personas-Korea importer examples that preserve
  `metadata.source_dataset` and `metadata.source_license`.
- Generic illustrative rubric axes and demo configs/personas.
- Root-level public docs, `LICENSE`, `NOTICE`, and clean-export audit tooling.

Public B4User-lite exports must exclude:

- AX adoption-friction scoring, industry-specific domain packs, advanced
  rubrics, Product Risk Profile, scale gates, ontology/promotion bridges, Sales
  Pack logic, evaluator training/ML/tuning, and PM/marketing decision
  frameworks.
- Private planning docs, decks, PDFs, DOCX/PPTX/XLSX files, generated outputs,
  raw/processed datasets, local runtime paths, private prompts, bridge commands,
  credentials, and full private Git history.

Recommended approach:

1. Keep `dailykim149656-source/B4User` private.
2. Create a temporary clean export directory from the current working tree.
3. Copy only the B4User-lite public/source/distribution subset into that export.
4. Exclude ignored private docs, generated outputs, local data, proprietary
   domain/evaluation logic, and credentials.
5. Run `python scripts/audit_b4user_lite_export.py <clean-export-dir>`.
6. Build and test from the clean export.
7. Create a new public GitHub repository.
8. Push the clean export as an initial public history.
9. Treat the public repo as a distribution mirror, not the internal planning repo.

Suggested public export allowlist:

```text
.github/workflows/
configs/
data/personas_sample.jsonl
data/responses_sample.jsonl
npm/b4user-cli/
scripts/audit_b4user_lite_export.py
scripts/build_python_package.ps1
src/b4user/
src/kpeh/assets/
src/kpeh/core/
src/kpeh/data_sources/nemotron_korea.py
src/kpeh/domain_packs/generic/
src/kpeh/llm/mock.py
src/kpeh/llm/config.py
src/kpeh/llm/base.py
tests/
.gitignore
LICENSE
NOTICE
PUBLIC_RELEASE.md
README.md
REPOSITORY_POLICY.md
pyproject.toml
```

The allowlist is not permission to copy every advanced module under those
directories. Only tests for the public subset should be copied. The clean export
must still pass `scripts/audit_b4user_lite_export.py` and a manual source review
before it is published.

Before pushing a public repo, inspect the exact file list:

```bash
git ls-files
```

For a clean export directory, inspect recursively before `git init`:

```bash
find . -maxdepth 3 -type f | sort
```

## Distribution package audit

Before publishing to npm/PyPI, check what will actually be distributed.

### npm wrapper

Run:

```bash
cd npm/b4user-cli
npm pack --dry-run
```

Expected behavior: only the small wrapper package should be included, for example:

```text
README.md
bin/b4user.cjs
package.json
scripts/install-python-package.cjs
```

### Python package

Run from repository root:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_python_package.ps1
python -m zipfile -l dist/*.whl
python - <<'PY'
import tarfile
from pathlib import Path
for p in Path('dist').glob('*.tar.gz'):
    print(f'## {p}')
    with tarfile.open(p) as t:
        for name in t.getnames():
            print(name)
PY
```

Check that package artifacts do not include private docs, presentations, raw data, generated outputs, or secrets.

## Pre-publication checklist

Before any public repo or package publication:

- [ ] Confirm the target is a new public repository, not the private working repo.
- [ ] Confirm `git status --short` is clean.
- [ ] Review all files that will be pushed or packaged.
- [ ] Run CI locally or in GitHub Actions.
- [ ] Inspect npm tarball contents with `npm pack --dry-run`.
- [ ] Inspect Python wheel/sdist contents.
- [ ] Run `python scripts/audit_b4user_lite_export.py <clean-export-dir>`.
- [ ] Search for secrets or private URLs.
- [ ] Confirm no private docs, decks, PDFs, DOCX files, or generated outputs are included.

## Current baseline

As of the cleanup commit, the private repo's current `main` HEAD no longer tracks the ignored local/private documentation files. The files remain available locally in the working directory but are ignored by Git.
