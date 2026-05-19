from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

EVALUATION_MODES = {
    "response_quality",
    "market_fit",
    "ax_discovery",
    "agent_concept",
    "agent_meeting",
    "repo_persona_analysis",
    "repo_persona_analysis_batch",
}


class ValidationError(ValueError):
    """Raised when input data cannot be converted into a B4User model."""


def _required(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "":
        raise ValidationError(f"Missing required field: {key}")
    return value


def _list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if item is not None and str(item) != ""]


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Expected integer value, got {value!r}") from exc


def _evaluation_mode(value: Any | None, default: str = "response_quality") -> str:
    mode = str(value or default)
    if mode not in EVALUATION_MODES:
        raise ValidationError(f"Unsupported evaluation_mode: {mode}")
    return mode


def to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: to_plain_data(item)
            for key, item in asdict(value).items()
            if item is not None and item != [] and item != {}
        }
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    return value


@dataclass(slots=True)
class PersonaRecord:
    persona_id: str
    persona: str
    age: int | None = None
    gender: str | None = None
    province: str | None = None
    city: str | None = None
    occupation: str | None = None
    industry: str | None = None
    education: str | None = None
    income_band: str | None = None
    digital_literacy: str | None = None
    technology_attitude: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonaRecord":
        known = {
            "persona_id",
            "persona",
            "age",
            "gender",
            "province",
            "city",
            "occupation",
            "industry",
            "education",
            "income_band",
            "digital_literacy",
            "technology_attitude",
            "metadata",
        }
        metadata = dict(data.get("metadata") or {})
        for key, value in data.items():
            if key not in known:
                metadata[key] = value
        return cls(
            persona_id=str(_required(data, "persona_id")),
            persona=str(_required(data, "persona")),
            age=_optional_int(data.get("age")),
            gender=data.get("gender") or None,
            province=data.get("province") or None,
            city=data.get("city") or None,
            occupation=data.get("occupation") or None,
            industry=data.get("industry") or None,
            education=data.get("education") or None,
            income_band=data.get("income_band") or None,
            digital_literacy=data.get("digital_literacy") or None,
            technology_attitude=data.get("technology_attitude") or None,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class LikelyConcern:
    name: str
    claim_type: str = "hypothesis"
    confidence: float = 0.6
    basis: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LikelyConcern":
        return cls(
            name=str(_required(data, "name")),
            claim_type=str(data.get("claim_type") or "hypothesis"),
            confidence=float(data.get("confidence", 0.6)),
            basis=_str_list(data.get("basis")),
        )


@dataclass(slots=True)
class PersonaProfile:
    profile_id: str
    persona_id: str
    segment: str
    summary: str
    communication_style: str
    likely_concerns: list[LikelyConcern]
    evaluation_focus: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonaProfile":
        return cls(
            profile_id=str(_required(data, "profile_id")),
            persona_id=str(_required(data, "persona_id")),
            segment=str(_required(data, "segment")),
            summary=str(_required(data, "summary")),
            communication_style=str(_required(data, "communication_style")),
            likely_concerns=[
                item if isinstance(item, LikelyConcern) else LikelyConcern.from_dict(item)
                for item in _list(data.get("likely_concerns"))
            ],
            evaluation_focus=_str_list(data.get("evaluation_focus")),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class ServiceSpec:
    service_id: str
    name: str
    description: str
    target_users: list[str] = field(default_factory=list)
    service_capabilities: list[str] = field(default_factory=list)
    known_limits: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceSpec":
        return cls(
            service_id=str(data.get("service_id") or "svc_001"),
            name=str(_required(data, "name")),
            description=str(_required(data, "description")),
            target_users=_str_list(data.get("target_users")),
            service_capabilities=_str_list(data.get("service_capabilities")),
            known_limits=_str_list(data.get("known_limits")),
            prohibited_claims=_str_list(data.get("prohibited_claims")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class AgentConcept:
    concept_id: str
    name: str
    description: str
    target_users: list[str] = field(default_factory=list)
    pricing: str | None = None
    capabilities: list[str] = field(default_factory=list)
    known_limits: list[str] = field(default_factory=list)
    onboarding: str | None = None
    prohibited_claims: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConcept":
        return cls(
            concept_id=str(data.get("concept_id") or data.get("service_id") or "concept_001"),
            name=str(_required(data, "name")),
            description=str(_required(data, "description")),
            target_users=_str_list(data.get("target_users")),
            pricing=data.get("pricing") or None,
            capabilities=_str_list(data.get("capabilities") or data.get("service_capabilities")),
            known_limits=_str_list(data.get("known_limits")),
            onboarding=data.get("onboarding") or None,
            prohibited_claims=_str_list(data.get("prohibited_claims")),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_service_spec(cls, service: ServiceSpec) -> "AgentConcept":
        return cls(
            concept_id=service.service_id,
            name=service.name,
            description=service.description,
            target_users=list(service.target_users),
            capabilities=list(service.service_capabilities),
            known_limits=list(service.known_limits),
            prohibited_claims=list(service.prohibited_claims),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class EvaluationScenario:
    scenario_id: str
    profile_id: str
    service_id: str
    situation: str
    user_goal: str
    context: dict[str, Any] = field(default_factory=dict)
    evaluation_mode: str = "response_quality"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationScenario":
        return cls(
            scenario_id=str(_required(data, "scenario_id")),
            profile_id=str(_required(data, "profile_id")),
            service_id=str(_required(data, "service_id")),
            situation=str(_required(data, "situation")),
            user_goal=str(_required(data, "user_goal")),
            context=dict(data.get("context") or {}),
            evaluation_mode=_evaluation_mode(data.get("evaluation_mode")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class SyntheticUserQuestion:
    question_id: str
    scenario_id: str
    profile_id: str
    question: str
    intent: str
    difficulty: str
    expected_good_answer_traits: list[str]
    risk_tags: list[str]
    evaluation_mode: str = "response_quality"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyntheticUserQuestion":
        traits = _str_list(data.get("expected_good_answer_traits"))
        if len(traits) < 2:
            raise ValidationError("SyntheticUserQuestion requires at least two expected_good_answer_traits")
        return cls(
            question_id=str(_required(data, "question_id")),
            scenario_id=str(_required(data, "scenario_id")),
            profile_id=str(_required(data, "profile_id")),
            question=str(_required(data, "question")),
            intent=str(_required(data, "intent")),
            difficulty=str(data.get("difficulty") or "medium"),
            expected_good_answer_traits=traits,
            risk_tags=_str_list(data.get("risk_tags")),
            evaluation_mode=_evaluation_mode(data.get("evaluation_mode")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class DiscoveryQuestion:
    question_id: str
    profile_id: str
    persona_id: str
    target_role: str
    question_type: str
    friction_axis: str
    question: str
    why_it_matters: str
    expected_signal: list[str]
    follow_up_questions: list[str]
    evaluation_mode: str = "ax_discovery"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiscoveryQuestion":
        mode = _evaluation_mode(data.get("evaluation_mode"), default="ax_discovery")
        if mode != "ax_discovery":
            raise ValidationError("DiscoveryQuestion requires evaluation_mode=ax_discovery")
        expected_signal = _str_list(data.get("expected_signal"))
        follow_up_questions = _str_list(data.get("follow_up_questions"))
        if not expected_signal:
            raise ValidationError("DiscoveryQuestion requires at least one expected_signal")
        if not follow_up_questions:
            raise ValidationError("DiscoveryQuestion requires at least one follow_up_question")
        return cls(
            question_id=str(_required(data, "question_id")),
            profile_id=str(_required(data, "profile_id")),
            persona_id=str(_required(data, "persona_id")),
            target_role=str(_required(data, "target_role")),
            question_type=str(_required(data, "question_type")),
            friction_axis=str(_required(data, "friction_axis")),
            question=str(_required(data, "question")),
            why_it_matters=str(_required(data, "why_it_matters")),
            expected_signal=expected_signal,
            follow_up_questions=follow_up_questions,
            evaluation_mode=mode,
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class TargetResponse:
    response_id: str
    question_id: str
    model_or_service: str
    response_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetResponse":
        return cls(
            response_id=str(data.get("response_id") or f"resp_{_required(data, 'question_id')}"),
            question_id=str(_required(data, "question_id")),
            model_or_service=str(data.get("model_or_service") or "target_service"),
            response_text=str(data.get("response_text") or ""),
            metadata=dict(data.get("metadata") or {}),
            status=str(data.get("status") or "completed"),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class RubricCriterion:
    name: str
    description: str
    score_min: int = 0
    score_max: int = 5
    reverse_score: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RubricCriterion":
        score_min = int(data.get("score_min", 0))
        score_max = int(data.get("score_max", 5))
        if score_max < score_min:
            raise ValidationError("Rubric criterion score_max must be >= score_min")
        return cls(
            name=str(_required(data, "name")),
            description=str(_required(data, "description")),
            score_min=score_min,
            score_max=score_max,
            reverse_score=bool(data.get("reverse_score", False)),
        )


@dataclass(slots=True)
class EvaluationRubric:
    rubric_id: str
    criteria: list[RubricCriterion]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationRubric":
        criteria = [RubricCriterion.from_dict(item) for item in _list(data.get("criteria"))]
        if not criteria:
            raise ValidationError("EvaluationRubric requires at least one criterion")
        return cls(rubric_id=str(_required(data, "rubric_id")), criteria=criteria)

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class EvaluationResult:
    result_id: str
    response_id: str | None
    question_id: str
    total_score: int
    max_score: int
    scores: dict[str, int]
    rationale: dict[str, str]
    failure_modes: list[str]
    improvement_suggestions: list[str]
    status: str = "completed"
    failure_mode_details: list[dict[str, Any]] = field(default_factory=list)
    evaluation_mode: str = "response_quality"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationResult":
        return cls(
            result_id=str(_required(data, "result_id")),
            response_id=data.get("response_id"),
            question_id=str(_required(data, "question_id")),
            total_score=int(data.get("total_score", 0)),
            max_score=int(data.get("max_score", 0)),
            scores={str(key): int(value) for key, value in dict(data.get("scores") or {}).items()},
            rationale={str(key): str(value) for key, value in dict(data.get("rationale") or {}).items()},
            failure_modes=_str_list(data.get("failure_modes")),
            improvement_suggestions=_str_list(data.get("improvement_suggestions")),
            status=str(data.get("status") or "completed"),
            failure_mode_details=list(data.get("failure_mode_details") or []),
            evaluation_mode=_evaluation_mode(data.get("evaluation_mode")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class SyntheticJudgeResult:
    judge_id: str
    response_id: str | None
    question_id: str
    profile_id: str
    target_name: str
    verdict: str
    trust_score: int
    usefulness_score: int
    adoption_friction: list[str]
    trust_risks: list[str]
    missing_information: list[str]
    persona_reaction: str
    rationale: str
    status: str = "completed"
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluation_mode: str = "response_quality"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyntheticJudgeResult":
        return cls(
            judge_id=str(_required(data, "judge_id")),
            response_id=data.get("response_id"),
            question_id=str(_required(data, "question_id")),
            profile_id=str(_required(data, "profile_id")),
            target_name=str(data.get("target_name") or "target_agent"),
            verdict=str(data.get("verdict") or "partial_trust"),
            trust_score=int(data.get("trust_score", 0)),
            usefulness_score=int(data.get("usefulness_score", 0)),
            adoption_friction=_str_list(data.get("adoption_friction")),
            trust_risks=_str_list(data.get("trust_risks")),
            missing_information=_str_list(data.get("missing_information")),
            persona_reaction=str(data.get("persona_reaction") or ""),
            rationale=str(data.get("rationale") or ""),
            status=str(data.get("status") or "completed"),
            metadata=dict(data.get("metadata") or {}),
            evaluation_mode=_evaluation_mode(data.get("evaluation_mode")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class AdoptionHypothesis:
    persona_id: str
    service_id: str
    adoption_likelihood: str
    primary_motivation: str
    primary_blocker: str
    trust_requirements: list[str]
    decision_style: str
    message_strategy: str
    claim_type: str = "hypothesis"
    confidence: float = 0.6

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdoptionHypothesis":
        return cls(
            persona_id=str(_required(data, "persona_id")),
            service_id=str(_required(data, "service_id")),
            adoption_likelihood=str(_required(data, "adoption_likelihood")),
            primary_motivation=str(_required(data, "primary_motivation")),
            primary_blocker=str(_required(data, "primary_blocker")),
            trust_requirements=_str_list(data.get("trust_requirements")),
            decision_style=str(_required(data, "decision_style")),
            message_strategy=str(_required(data, "message_strategy")),
            claim_type=str(data.get("claim_type") or "hypothesis"),
            confidence=float(data.get("confidence", 0.6)),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(slots=True)
class ConceptEvaluationResult:
    result_id: str
    concept_id: str
    persona_id: str
    evaluation_mode: str
    scores: dict[str, int]
    market_fit_score: float
    purchase_blockers: list[str]
    retention_risk: str
    recommended_message: str
    rationale: dict[str, str]
    adoption_hypothesis: AdoptionHypothesis | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConceptEvaluationResult":
        hypothesis = data.get("adoption_hypothesis")
        return cls(
            result_id=str(_required(data, "result_id")),
            concept_id=str(_required(data, "concept_id")),
            persona_id=str(_required(data, "persona_id")),
            evaluation_mode=_evaluation_mode(data.get("evaluation_mode"), default="market_fit"),
            scores={str(key): int(value) for key, value in dict(data.get("scores") or {}).items()},
            market_fit_score=float(data.get("market_fit_score", 0.0)),
            purchase_blockers=_str_list(data.get("purchase_blockers")),
            retention_risk=str(data.get("retention_risk") or ""),
            recommended_message=str(data.get("recommended_message") or ""),
            rationale={str(key): str(value) for key, value in dict(data.get("rationale") or {}).items()},
            adoption_hypothesis=AdoptionHypothesis.from_dict(hypothesis) if isinstance(hypothesis, dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)
