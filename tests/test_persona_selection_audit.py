from __future__ import annotations

from kpeh.core.models import PersonaProfile, ServiceSpec
from kpeh.core.persona_selection_audit import build_persona_selection_audit, markdown_lines_from_audit


def _profile(
    persona_id: str,
    *,
    segment: str = "decision_maker",
    score: float | None = 0.7,
    occupation: str = "owner",
) -> PersonaProfile:
    metadata = {
        "source_fields": {
            "age": 38,
            "province": "Seoul",
            "occupation": occupation,
            "persona": "Small business owner who wants to automate repetitive customer work.",
            "digital_literacy": "medium",
        },
        "panel_metadata": {"quota_bucket": segment},
    }
    if score is not None:
        metadata["sampling_scores"] = {"domain_relevance_score": score}
    return PersonaProfile(
        profile_id=f"profile_{persona_id}",
        persona_id=persona_id,
        segment=segment,
        summary="Small business owner evaluating automation support.",
        communication_style="direct",
        likely_concerns=[],
        evaluation_focus=[],
        metadata=metadata,
    )


def test_persona_selection_audit_records_target_definition_and_validation_decision():
    service = ServiceSpec(
        service_id="svc_automation",
        name="Automation advisor",
        description="Helps small business owners assess automation fit.",
        target_users=["small business owner"],
        service_capabilities=["workflow diagnosis"],
        known_limits=["requires human review"],
        prohibited_claims=["guaranteed revenue growth"],
    )

    audit = build_persona_selection_audit(
        profiles=[_profile("p1"), _profile("p2", score=0.8), _profile("p3", score=0.65)],
        sampling_strategy={
            "strategy": "panel",
            "quota": {"decision_maker": 1.0},
            "coverage": {"age_band": {"30s": {"min": 1}}},
        },
        requested_n=3,
        seed=7,
        target=service,
    )

    assert audit["target_definition"]["target_type"] == "service_spec"
    assert audit["target_definition"]["target_users"] == ["small business owner"]
    assert audit["target_fit"]["basis"] == "panel_domain_relevance_score"
    assert audit["validation_decision"]["status"] == "usable_for_synthetic_exploration"
    assert audit["validation_decision"]["confidence"] == "medium"
    assert audit["human_review_checklist"]

    markdown = "\n".join(markdown_lines_from_audit(audit))
    assert "Target Definition" in markdown
    assert "Validation Decision" in markdown
    assert "validation_decision: usable_for_synthetic_exploration" in markdown


def test_persona_selection_audit_blocks_target_claims_without_target_or_fit_signal():
    audit = build_persona_selection_audit(
        profiles=[_profile("p1", segment="general_user", score=None, occupation="")],
        sampling_strategy="random",
        requested_n=3,
        seed=1,
        target=None,
    )

    assert audit["target_definition"]["target_type"] == "not_provided"
    assert audit["target_fit"]["basis"] == "strategy_has_no_target_fit_signal"
    assert audit["validation_decision"]["status"] == "insufficient_for_target_claims"
    assert "target_fit_needs_review" in audit["validation_decision"]["blocking_issues"]
    assert "target_not_provided" in audit["validation_decision"]["review_issues"]
    assert audit["human_review_queue"][0]["persona_id"] == "p1"

    markdown = "\n".join(markdown_lines_from_audit(audit))
    assert "Do not use this run for target-user claims" in markdown
