from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NPM_PACKAGE = REPO_ROOT / "npm" / "b4user-cli"


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}


def test_python_module_entrypoint_runs_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "b4user", "--help"],
        cwd=REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "B4User-lite synthetic persona validation harness" in result.stdout
    assert "import-nemotron" in result.stdout


def test_python_package_declares_public_license_metadata() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["license"] == {"file": "LICENSE"}
    assert "License :: OSI Approved :: Apache Software License" in pyproject["project"]["classifiers"]
    assert "nvidia/Nemotron-Personas-Korea" in (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert (REPO_ROOT / "README.ko.md").exists()
    assert "이걸로 할 수 있는 것" in (REPO_ROOT / "README.ko.md").read_text(encoding="utf-8")


def test_npm_cli_package_uses_public_license() -> None:
    package_json = json.loads((NPM_PACKAGE / "package.json").read_text(encoding="utf-8"))
    assert package_json["name"] == "@b4user/cli"
    assert package_json["license"] == "Apache-2.0"
    assert package_json["bin"]["b4user"] == "bin/b4user.cjs"


def test_lite_pipeline_smoke(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "b4user",
            "run",
            "--personas",
            "data/personas_sample.jsonl",
            "--service",
            "configs/service.yaml",
            "--domain-pack",
            "generic",
            "--n-personas",
            "3",
            "--questions-per-persona",
            "1",
            "--output-dir",
            str(out),
            "--seed",
            "42",
        ],
        cwd=REPO_ROOT,
        env=_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (out / "questions.jsonl").exists()
    assert (out / "evaluation_results.jsonl").exists()
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "# B4User Evaluation Report" in report
