from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from dataclasses import dataclass
from pathlib import Path


SKIPPED_DIRS = {
    ".agents",
    ".claude",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

FORBIDDEN_DIRS = {
    ".agents",
    ".claude",
    ".mypy_cache",
    ".omx",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "outputs",
}

FORBIDDEN_TREE_DIRS = {
    ".omx",
    "PT",
    "data/processed",
    "data/raw",
    "docs",
    "frontend/playwright-report",
    "frontend/test-results",
    "outputs",
}

REQUIRED_PATHS = {
    "LICENSE",
    "NOTICE",
    "PUBLIC_RELEASE.md",
    "README.md",
    "REPOSITORY_POLICY.md",
    "pyproject.toml",
    "scripts/audit_b4user_lite_export.py",
    "src/kpeh/data_sources/nemotron_korea.py",
    "src/kpeh/domain_packs/generic/rubrics.yaml",
}

FORBIDDEN_PATTERNS = {
    ".env",
    ".env.*",
    ".omx/*",
    "PRD.md",
    "PT/*",
    "data/raw/*",
    "data/processed/*",
    "docs/*",
    "outputs/*",
    "*.doc",
    "*.docx",
    "*.key",
    "*.pdf",
    "*.ppt",
    "*.pptx",
    "*.xls",
    "*.xlsx",
    "*.zip",
}

PRIVATE_SOURCE_PATTERNS = {
    "src/kpeh/domain_packs/ax_discovery/*",
    "src/kpeh/domain_packs/manufacturing_ax/*",
    "src/kpeh/domain_packs/small_business_automation/*",
    "src/kpeh/core/agent_meeting.py",
    "src/kpeh/core/ax_discovery.py",
    "src/kpeh/core/evaluator_*.py",
    "src/kpeh/core/live_evaluator.py",
    "src/kpeh/core/llm_tuning.py",
    "src/kpeh/core/market_fit.py",
    "src/kpeh/core/onepager_generator.py",
    "src/kpeh/core/product_risk.py",
    "src/kpeh/core/sales_report_generator.py",
    "src/kpeh/core/scale_gate.py",
    "src/kpeh/core/segment_insight_builder.py",
    "src/kpeh/core/training_*.py",
    "src/kpeh/ontology/*",
}

SECRET_MARKERS = {
    "OPENAI_API_KEY=",
    "sk-",
    "nvapi-",
    "B4USER_HERMES_RUNTIME_ALLOWLIST=",
    "KPEH_HERMES_RUNTIME_ALLOWLIST=",
    "hermes_bridge_command",
}

SYNTHETIC_WARNING_MARKERS = {
    "synthetic persona",
    "합성 페르소나",
}


@dataclass(frozen=True)
class AuditResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    files_checked: int

    @property
    def ok(self) -> bool:
        return not self.errors


def audit_export(root: Path) -> AuditResult:
    root = root.resolve()
    if not root.exists():
        return AuditResult((f"export root does not exist: {root}",), (), 0)
    if not root.is_dir():
        return AuditResult((f"export root is not a directory: {root}",), (), 0)

    rel_paths = sorted(_iter_relative_files(root))
    rel_set = set(rel_paths)
    errors: list[str] = []
    warnings: list[str] = []

    for directory in sorted(FORBIDDEN_DIRS):
        if (root / directory).exists():
            errors.append(f"forbidden private/generated directory: {directory}")
    for directory in sorted(FORBIDDEN_TREE_DIRS):
        if (root / directory).exists():
            errors.append(f"forbidden private/generated directory: {directory}")

    missing = sorted(REQUIRED_PATHS - rel_set)
    errors.extend(f"missing required public file: {path}" for path in missing)

    for rel_path in rel_paths:
        if _matches(rel_path, FORBIDDEN_PATTERNS):
            errors.append(f"forbidden private/generated file: {rel_path}")
        if _matches(rel_path, PRIVATE_SOURCE_PATTERNS):
            errors.append(f"proprietary source surface in lite export: {rel_path}")
        if rel_path == "scripts/audit_b4user_lite_export.py":
            continue
        if _looks_binary(rel_path):
            continue
        text = _read_text(root / rel_path)
        if text is None:
            warnings.append(f"could not read text for marker scan: {rel_path}")
            continue
        for marker in SECRET_MARKERS:
            if marker in text:
                errors.append(f"secret or private runtime marker found in {rel_path}: {marker}")

    readme = _read_text(root / "README.md") or ""
    public_release = _read_text(root / "PUBLIC_RELEASE.md") or ""
    combined_docs = f"{readme}\n{public_release}"
    if not any(marker in combined_docs for marker in SYNTHETIC_WARNING_MARKERS):
        errors.append("public docs must include synthetic-persona warning wording")
    if "Apache-2.0" not in ((_read_text(root / "pyproject.toml") or "") + "\n" + readme + "\n" + public_release):
        errors.append("public docs or pyproject must declare Apache-2.0")
    if "nvidia/Nemotron-Personas-Korea" not in ((_read_text(root / "NOTICE") or "") + "\n" + public_release):
        errors.append("NOTICE or PUBLIC_RELEASE.md must attribute nvidia/Nemotron-Personas-Korea")
    if "cc-by-4.0" not in (_read_text(root / "src/kpeh/data_sources/nemotron_korea.py") or "").lower():
        errors.append("Nemotron importer must preserve cc-by-4.0 source license metadata")

    return AuditResult(tuple(errors), tuple(warnings), len(rel_paths))


def _iter_relative_files(root: Path) -> list[str]:
    files: list[str] = []
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        kept_dirnames: list[str] = []
        for dirname in dirnames:
            rel_dir = (current / dirname).relative_to(root).as_posix()
            if dirname in SKIPPED_DIRS or rel_dir in FORBIDDEN_TREE_DIRS:
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for filename in filenames:
            files.append((current / filename).relative_to(root).as_posix())
    return files


def _matches(rel_path: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatchcase(rel_path, pattern) for pattern in patterns)


def _looks_binary(rel_path: str) -> bool:
    return Path(rel_path).suffix.lower() in {
        ".ico",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".woff",
        ".woff2",
    }


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a clean B4User-lite public export directory")
    parser.add_argument("export_root", help="Path to the candidate clean export directory")
    args = parser.parse_args(argv)

    result = audit_export(Path(args.export_root))
    print(f"files_checked={result.files_checked}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for error in result.errors:
        print(f"error: {error}")
    if result.ok:
        print("b4user_lite_export_audit=pass")
        return 0
    print("b4user_lite_export_audit=fail")
    return 1


if __name__ == "__main__":
    sys.exit(main())
