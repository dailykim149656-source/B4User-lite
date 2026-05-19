# B4User-lite

[English README](README.md)

B4User-lite는 실제 배포 전에 agent, 제품 컨셉, 응답 패턴이 한국어 synthetic persona 앞에서 버틸 수 있는지 점검하는 Apache-2.0 공개용 pre-user validation harness입니다.

이 프로젝트는 또 하나의 persona survey 도구가 아닙니다. 합성 사용자에게 구조화된 질문을 만들고, 대상 agent나 제품 응답을 수집하고, 기본 루브릭으로 평가한 뒤, 사람이 검토할 수 있는 evidence artifact를 남기는 작고 반복 가능한 하네스입니다.

> Synthetic users are not real users. B4User-lite 결과는 synthetic persona 기반 평가 가설입니다. 실제 사용자 조사, 시장 수요 검증, 직원 인터뷰, 법무 검토, 보안 검토, production safety review를 대체하지 않습니다.

## 이걸로 할 수 있는 것

- JSONL persona와 YAML service spec으로 한국어 synthetic-user 질문을 만들 수 있습니다.
- API key 없이 mock target response를 사용해 deterministic local evaluation을 실행할 수 있습니다.
- 이미 수집한 agent/product 응답을 generic response-quality rubric으로 평가할 수 있습니다.
- Markdown report와 JSONL artifact를 만들어 사람이 검토할 수 있습니다.
- 선택 dependency를 설치하면 `nvidia/Nemotron-Personas-Korea`에서 persona sample을 import할 수 있습니다.
- public-export audit으로 공개본에 private docs, generated outputs, credential, proprietary evaluation surface가 섞였는지 검사할 수 있습니다.

## 포함된 것

- lite workflow용 `b4user` CLI
- JSONL persona loader와 YAML/JSON service config loader
- deterministic persona sampling, persona compilation, scenario generation, question generation
- offline smoke test용 mock response collection
- 기본 response-quality scoring
- `clarity`, `actionability`, `risk_disclosure`, `persona_fit` 중심의 generic illustrative rubric
- synthetic-hypothesis 경고문이 포함된 Markdown report
- Nemotron-Personas-Korea importer와 source attribution metadata
- Python CLI 실행을 위한 npm wrapper source

## 의도적으로 제외한 것

private B4User working repository는 공개하지 않았습니다. B4User-lite에는 고급 평가 루브릭, AX 도입 마찰 스코어링, 산업별 domain pack, Product Risk Profile, evaluator training, ontology/promotion bridge, Sales Pack logic, generated artifact, private planning docs, raw dataset, processed dataset이 포함되지 않습니다.

이 repo는 전체 내부 제품이 아니라 공개 가능한 B4User-lite 경계입니다.

## 개발 설치

요구사항:

- Python 3.11+
- npm wrapper를 확인하거나 패키징하려면 Node.js 18+

```powershell
python -m pip install -e ".[dev]"
python -m b4user --help
```

Nemotron/Hugging Face import를 쓰려면 선택 dependency를 설치합니다.

```powershell
python -m pip install -e ".[dev,hf]"
```

## 빠른 실행

deterministic local demo를 실행합니다.

```powershell
b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42
```

생성물은 Git에서 무시되는 `outputs/` 아래에 만들어집니다.

주요 output:

- `profiles.jsonl`: synthetic-user profile
- `scenarios.jsonl`: profile별 평가 상황
- `questions.jsonl`: 생성된 synthetic-user 질문
- `target_responses.jsonl`: 제공된 응답 또는 mock 응답
- `evaluation_results.jsonl`: rubric score와 failure signal
- `report.md`: 사람이 읽을 수 있는 synthetic-evidence report
- `run_config.json`: synthetic-hypothesis warning이 포함된 run metadata

## CLI 명령

질문만 생성:

```powershell
b4user generate-questions --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 10 --questions-per-persona 2 --output outputs/questions.jsonl --seed 42
```

기존 응답 평가:

```powershell
b4user evaluate --questions outputs/questions.jsonl --responses data/responses_sample.jsonl --rubric generic --failure-modes generic --output outputs/evaluation_results.jsonl
```

Markdown report 생성:

```powershell
b4user report --results outputs/evaluation_results.jsonl --profiles outputs/profiles.jsonl --scenarios outputs/scenarios.jsonl --questions outputs/questions.jsonl --service configs/service.yaml --output outputs/report.md
```

Nemotron persona import:

```powershell
b4user import-nemotron --n 100 --seed 42 --output data/processed/nemotron_sample.jsonl
```

`data/processed/`는 Git에서 무시됩니다. 외부 dataset row를 commit하기 전에는 license, attribution, privacy implication을 반드시 검토하세요.

## 입력 형식

Persona는 JSONL record입니다.

```json
{"persona_id":"kr_000001","age":47,"gender":"female","province":"전라북도","city":"전주시","occupation":"제조업 사무직","digital_literacy":"medium","persona":"반복적인 엑셀 정리 업무를 줄이고 싶지만 비용과 유지보수 조건을 확인하고 싶어한다."}
```

Service spec은 YAML입니다.

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

## Nemotron attribution

Importer는 CC BY 4.0으로 공개된 NVIDIA의 별도 dataset인 `nvidia/Nemotron-Personas-Korea`를 대상으로 합니다. 변환된 record는 다음 metadata를 유지합니다.

- `metadata.source_dataset`
- `metadata.source_license`
- `metadata.source_fields`

## Public export audit

수정한 공개본을 배포하기 전에는 다음을 실행합니다.

```powershell
python scripts/audit_b4user_lite_export.py .
python -m pytest
```

Audit은 공개본이 lite 경계를 지키는지 검사합니다. private docs, generated artifacts, raw/processed datasets, credentials, proprietary domain packs, advanced private evaluation surfaces가 섞이면 실패합니다.

## License

B4User-lite는 Apache-2.0으로 공개됩니다. [LICENSE](LICENSE)와 [NOTICE](NOTICE)를 확인하세요.
