from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_b4user_lite_export.py"


def test_public_export_audit_accepts_minimal_lite_export(tmp_path: Path) -> None:
    _write_minimal_lite_export(tmp_path)

    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "b4user_lite_export_audit=pass" in result.stdout


def test_public_export_audit_rejects_private_surfaces(tmp_path: Path) -> None:
    _write_minimal_lite_export(tmp_path)
    api_key_name = "OPENAI" + "_API_KEY"
    fake_secret = "s" + "k-test"
    _write(tmp_path / ".env", f"{api_key_name}={fake_secret}\n")
    _write(tmp_path / "docs" / "PRIVATE.md", "private planning\n")
    _write(tmp_path / "src" / "kpeh" / "domain_packs" / "small_business_automation" / "rubrics.yaml", "private: true\n")
    _write(tmp_path / "src" / "kpeh" / "core" / "product_risk.py", "RISK = 'private'\n")

    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "forbidden private/generated file: .env" in result.stdout
    assert "forbidden private/generated directory: docs" in result.stdout
    assert "proprietary source surface in lite export" in result.stdout
    assert api_key_name + "=" in result.stdout


def _write_minimal_lite_export(root: Path) -> None:
    _write(root / "LICENSE", "Apache License\nVersion 2.0\n")
    _write(
        root / "NOTICE",
        "B4User\nnvidia/Nemotron-Personas-Korea\nThe dataset is CC BY 4.0.\n",
    )
    _write(
        root / "PUBLIC_RELEASE.md",
        "B4User-lite uses Apache-2.0. synthetic persona outputs are hypotheses. "
        "Source: nvidia/Nemotron-Personas-Korea.\n",
    )
    _write(root / "README.md", "B4User synthetic persona evaluation. Apache-2.0.\n")
    _write(root / "REPOSITORY_POLICY.md", "clean export only\n")
    _write(root / "pyproject.toml", "[project]\nname = 'b4user'\nlicense = { file = 'LICENSE' }\n")
    _write(root / "scripts" / "audit_b4user_lite_export.py", "# audit tool placeholder\n")
    _write(root / "src" / "kpeh" / "data_sources" / "nemotron_korea.py", "SOURCE_LICENSE = 'cc-by-4.0'\n")
    _write(root / "src" / "kpeh" / "domain_packs" / "generic" / "rubrics.yaml", "criteria: []\n")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
