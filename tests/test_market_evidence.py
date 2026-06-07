from __future__ import annotations

from kpeh.core.market_evidence import (
    build_report_decision_brief,
    load_market_evidence,
    markdown_lines_from_decision_brief,
    markdown_lines_from_market_evidence,
)
from kpeh.core.models import ServiceSpec


def test_market_evidence_csv_loads_and_classifies_conversion_level(tmp_path):
    evidence_path = tmp_path / "market_evidence.csv"
    evidence_path.write_text(
        "source,signal_type,label,value,period,region,client_secret\n"
        "naver_datalab,search_trend,customer automation,72,2026-05,KR,do-not-store\n"
        "landing,signup,waitlist signup,14,2026-05,KR,do-not-store\n",
        encoding="utf-8",
    )

    evidence = load_market_evidence(evidence_path)

    assert evidence is not None
    assert evidence["record_count"] == 2
    assert evidence["evidence_level"]["level"] == "L3"
    assert evidence["claim_limit"].startswith("You may claim early conversion evidence")
    assert "client_secret" not in str(evidence["records"])

    markdown = "\n".join(markdown_lines_from_market_evidence(evidence))
    assert "Market Evidence" in markdown
    assert "evidence_level: L3" in markdown


def test_decision_brief_limits_claims_when_market_evidence_is_missing():
    service = ServiceSpec(
        service_id="svc_automation",
        name="Automation advisor",
        description="Helps small business owners assess automation fit.",
        target_users=["small business owner"],
        service_capabilities=["workflow diagnosis"],
        known_limits=["requires human review"],
    )

    brief = build_report_decision_brief(
        evaluation_mode="response_quality",
        target=service,
        synthetic_score=78,
        selection_audit={
            "validation_decision": {
                "status": "usable_for_synthetic_exploration",
                "blocking_issues": [],
                "review_issues": [],
            }
        },
        market_evidence=None,
    )

    assert brief["recommended_decision"] == "narrow_and_test"
    assert brief["confidence"] == "low"
    assert brief["evidence_level"]["level"] == "L0"
    assert any("conversion" in item for item in brief["why_this_may_be_wrong"])

    markdown = "\n".join(markdown_lines_from_decision_brief(brief))
    assert "Decision Brief" in markdown
    assert "Claim Ledger" in markdown
    assert "Why This May Be Wrong" in markdown
