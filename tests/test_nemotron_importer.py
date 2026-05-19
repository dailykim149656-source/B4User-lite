from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from kpeh.cli import main
from kpeh.core.io_utils import read_jsonl
from kpeh.core.models import PersonaRecord, ValidationError
from kpeh.core.persona_compiler import compile_persona
from kpeh.data_sources.nemotron_korea import convert_nemotron_row, import_nemotron_personas


def nemotron_row(uuid: str = "abc123", persona: str = "서울에서 일하는 회계 사무원") -> dict[str, object]:
    return {
        "uuid": uuid,
        "persona": persona,
        "age": 71,
        "sex": "여자",
        "occupation": "회계 사무원",
        "district": "서울-서초구",
        "province": "서울",
        "education_level": "4년제 대학교",
        "professional_persona": "부동산 사무실에서 장부와 세금 계산을 처리하는 회계 사무원입니다.",
        "cultural_background": "체면과 질서를 중시하는 분위기에 익숙합니다.",
        "skills_and_expertise": "복식부기 기반 장부 작성과 빠른 수치 검증에 능숙합니다.",
        "skills_and_expertise_list": ["복식부기", "수치 검증"],
        "hobbies_and_interests": "동네 산책과 문화센터 활동을 즐깁니다.",
        "career_goals_and_ambitions": "규칙적으로 출근하며 실무 노하우를 전수하고 싶어 합니다.",
    }


def test_convert_nemotron_row_maps_required_fields_and_metadata():
    converted = convert_nemotron_row(nemotron_row())

    record = PersonaRecord.from_dict(converted)

    assert record.persona_id == "abc123"
    assert record.persona == "서울에서 일하는 회계 사무원"
    assert record.gender == "여자"
    assert record.city == "서울-서초구"
    assert record.education == "4년제 대학교"
    assert record.metadata["source_dataset"] == "nvidia/Nemotron-Personas-Korea"
    assert record.metadata["source_license"] == "cc-by-4.0"
    assert record.metadata["source_fields"]["professional_persona"].startswith("부동산")
    assert record.metadata["source_fields"]["skills_and_expertise_list"] == ["복식부기", "수치 검증"]


def test_convert_nemotron_row_requires_uuid_and_persona():
    with pytest.raises(ValidationError, match="uuid"):
        convert_nemotron_row(nemotron_row(uuid=""))
    with pytest.raises(ValidationError, match="persona"):
        convert_nemotron_row(nemotron_row(persona=""))


def test_compiler_uses_nemotron_metadata_as_basis():
    record = PersonaRecord.from_dict(convert_nemotron_row(nemotron_row()))

    profile = compile_persona(record, index=1)

    bases = {basis for concern in profile.likely_concerns for basis in concern.basis}
    assert "professional_persona" in bases
    assert "skills_and_expertise" in bases
    assert profile.metadata["source_fields"]["source_dataset"] == "nvidia/Nemotron-Personas-Korea"


def test_import_nemotron_personas_uses_mocked_datasets_module(tmp_path, monkeypatch):
    rows = [nemotron_row(uuid=f"id_{index}") for index in range(10)]

    def fake_load_dataset(dataset, split, streaming):
        assert dataset == "fake/nemotron"
        assert split == "train"
        assert streaming is True
        return iter(rows)

    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(load_dataset=fake_load_dataset))
    output = tmp_path / "nemotron.jsonl"

    summary = import_nemotron_personas(
        output,
        dataset="fake/nemotron",
        split="train",
        n=3,
        seed=123,
        max_source_rows=5,
    )

    converted = read_jsonl(output)
    assert summary.converted_count == 3
    assert summary.source_rows_scanned == 5
    assert len(converted) == 3
    assert (tmp_path / "nemotron.jsonl.summary.json").exists()


def test_cli_import_nemotron_uses_mocked_datasets_module(tmp_path, monkeypatch):
    rows = [nemotron_row(uuid=f"id_{index}") for index in range(4)]
    monkeypatch.setitem(
        sys.modules,
        "datasets",
        SimpleNamespace(load_dataset=lambda dataset, split, streaming: iter(rows)),
    )
    output = tmp_path / "cli_nemotron.jsonl"

    assert (
        main(
            [
                "import-nemotron",
                "--dataset",
                "fake/nemotron",
                "--split",
                "train",
                "--n",
                "2",
                "--seed",
                "42",
                "--max-source-rows",
                "4",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert len(read_jsonl(output)) == 2
