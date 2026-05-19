<p align="center">
  <img src="assets/b4user-logo.svg" alt="B4User-lite logo" width="420">
</p>

# B4User-lite

[English README](README.md)

B4User-lite는 실제 사용자에게 배포하기 전, 에이전트와 제품 컨셉을 한국어 합성 페르소나로 사전 점검하는 공개용 pre-user validation harness입니다. 응답 방식이 어떻게 받아들여지는지 재현 가능하게 살펴볼 수 있습니다. 라이선스는 Apache-2.0입니다.

B4User-lite는 단순한 페르소나 설문 도구가 아닙니다. 구조화된 질문을 만들고, 대상 에이전트나 제품 응답을 모읍니다. 그런 다음 예시용 기본 루브릭으로 점검해, 사람이 다시 읽을 수 있는 근거 산출물을 남깁니다.

> Synthetic users are not real users. B4User-lite의 결과는 합성 페르소나 기반 평가 가설입니다. 실제 사용자 조사, 시장 수요 검증, 직원 인터뷰, 법무 검토, 보안 검토, production safety review를 대체하지 않습니다.

## 이걸로 할 수 있는 것

- JSONL persona와 YAML service spec을 바탕으로 한국어 synthetic-user 질문을 생성합니다.
- API key 없이 mock target response로 재현 가능한 로컬 평가를 실행합니다.
- 이미 모아 둔 에이전트 또는 제품 응답을 generic response-quality rubric으로 점검합니다.
- Markdown report와 JSONL artifact를 만들어 사람이 검토할 수 있는 기록을 남깁니다.
- 선택 의존성을 설치하면 `nvidia/Nemotron-Personas-Korea`에서 persona sample을 가져올 수 있습니다.

## 포함된 것

- lite workflow용 `b4user` CLI
- JSONL persona loader와 YAML/JSON service config loader
- deterministic persona sampling, persona compilation, scenario generation, question generation
- offline smoke test용 mock response collection
- 기본 response-quality scoring
- `clarity`, `actionability`, `risk_disclosure`, `persona_fit` 중심의 generic illustrative rubric
- synthetic-hypothesis 경고문이 포함된 Markdown report
- Nemotron-Personas-Korea importer와 source attribution metadata
- Python CLI를 실행하기 위한 npm wrapper source

## 개발 설치

요구사항:

- Python 3.11+
- npm wrapper를 확인하거나 패키징하려면 Node.js 18+

```powershell
python -m pip install -e ".[dev]"
python -m b4user --help
```

Nemotron/Hugging Face import를 쓰려면 선택 의존성을 설치합니다.

```powershell
python -m pip install -e ".[dev,hf]"
```

## 빠른 실행

재현 가능한 로컬 demo를 실행합니다.

```powershell
b4user run --personas data/personas_sample.jsonl --service configs/service.yaml --domain-pack generic --n-personas 20 --questions-per-persona 2 --output-dir outputs/demo --seed 42
```

생성물은 Git에서 무시되는 `outputs/` 아래에 만들어집니다.

주요 출력물:

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

`data/processed/`는 Git에서 무시됩니다. 외부 데이터셋 row를 commit하기 전에는 라이선스, 출처 표기, 개인정보/재배포 이슈를 반드시 검토하세요.

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

## License

B4User-lite는 Apache-2.0으로 공개됩니다. [LICENSE](LICENSE)와 [NOTICE](NOTICE)를 확인하세요.
