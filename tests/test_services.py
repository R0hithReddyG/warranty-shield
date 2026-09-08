"""
Tests for the claim service layer and agent fallback processing.
"""

from datetime import datetime, timedelta

import pytest

from app.models import ClaimCategory, ClaimStatus, RiskLevel, WarrantyClaim
from app.services import ClaimService
from app.services.langgraph_agent import process_claim


@pytest.fixture
def make_claim():
    """Factory fixture for building claims with sensible defaults."""

    def _make(claim_id: str = "WC-SVC-001", **overrides) -> WarrantyClaim:
        defaults = {
            "product_name": "Test Product",
            "product_serial": "SN12345678",
            "purchase_date": datetime.now() - timedelta(days=60),
            "claim_date": datetime.now(),
            "category": ClaimCategory.DEFECTIVE,
            "description": "Product is not working properly",
            "amount": 1000.0,
            "customer_id": "CUST-001",
            "prior_claims": 0,
            "prior_claim_value": 0.0,
        }
        defaults.update(overrides)
        return WarrantyClaim(claim_id=claim_id, **defaults)

    return _make


@pytest.fixture
def claim_service():
    """Create a fresh ClaimService instance."""
    return ClaimService()


class TestClaimService:
    """Tests for the ClaimService class."""

    def test_create_claim_assigns_score(self, claim_service, make_claim):
        claim = claim_service.create_claim(make_claim())

        assert claim.claim_id == "WC-SVC-001"
        assert claim.risk_score > 0
        assert claim.risk_level is not None
        assert claim.status == ClaimStatus.PENDING

    def test_get_claim(self, claim_service, make_claim):
        claim = claim_service.create_claim(make_claim())
        fetched = claim_service.get_claim("WC-SVC-001")

        assert fetched is not None
        assert fetched.claim_id == claim.claim_id

    def test_get_claim_missing(self, claim_service):
        assert claim_service.get_claim("DOES-NOT-EXIST") is None

    def test_update_status(self, claim_service, make_claim):
        claim_service.create_claim(make_claim())
        updated = claim_service.update_status("WC-SVC-001", ClaimStatus.APPROVED)

        assert updated is not None
        assert updated.status == ClaimStatus.APPROVED

    def test_recompute_score(self, claim_service, make_claim):
        claim_service.create_claim(make_claim())
        result = claim_service.recompute_score("WC-SVC-001")

        assert result is not None
        assert 0 <= result.total_score <= 100

    def test_recompute_score_missing(self, claim_service):
        assert claim_service.recompute_score("DOES-NOT-EXIST") is None

    def test_list_claims_sorted_by_risk(self, claim_service, make_claim):
        low = claim_service.create_claim(make_claim("WC-SVC-LOW", amount=100.0))
        high = claim_service.create_claim(
            make_claim(
                "WC-SVC-HIGH",
                amount=5000.0,
                category=ClaimCategory.LOST_OR_STOLEN,
                description="stolen urgent cash refund",
                prior_claims=5,
                prior_claim_value=9000.0,
            )
        )

        claims = claim_service.list_claims()
        assert claims[0].claim_id == high.claim_id
        assert claims[-1].claim_id == low.claim_id

    def test_list_claims_filter_by_risk_level(self, claim_service, make_claim):
        claim_service.create_claim(make_claim("WC-SVC-LOW", amount=100.0))
        claim_service.create_claim(
            make_claim(
                "WC-SVC-HIGH",
                amount=5000.0,
                category=ClaimCategory.LOST_OR_STOLEN,
                description="stolen urgent cash refund",
                prior_claims=5,
                prior_claim_value=9000.0,
            )
        )

        high_claims = claim_service.list_claims(risk_level=RiskLevel.HIGH)
        assert all(c.risk_level == RiskLevel.HIGH for c in high_claims)
        assert len(high_claims) == 1

    def test_get_escalated_claims(self, claim_service, make_claim):
        claim_service.create_claim(make_claim("WC-SVC-LOW", amount=100.0))
        claim_service.create_claim(
            make_claim(
                "WC-SVC-HIGH",
                amount=5000.0,
                category=ClaimCategory.LOST_OR_STOLEN,
                description="stolen urgent cash refund",
                prior_claims=5,
                prior_claim_value=9000.0,
            )
        )

        escalated = claim_service.get_escalated_claims()
        assert {c.claim_id for c in escalated} == {"WC-SVC-HIGH"}

    def test_emit_agent_event(self, claim_service, make_claim):
        claim_service.create_claim(make_claim())
        event = claim_service.emit_agent_event(
            "scoring_complete", "WC-SVC-001", data={"score": 42}, step="score"
        )

        assert event.event_type == "scoring_complete"
        assert event.claim_id == "WC-SVC-001"
        assert event.data == {"score": 42}


class TestAgentProcessing:
    """Tests for the LangGraph agent fallback path (agent disabled by default)."""

    def test_process_claim_disabled_fallback(self, make_claim):
        claim = make_claim("WC-AGENT-001")
        result = process_claim(claim.model_dump(mode="json"))

        assert result["decision"] in {"approve", "review", "escalate"}
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_level"] in {"low", "medium", "high", "critical"}
        assert result["reason"]

    def test_process_claim_high_risk_escalates(self, make_claim):
        claim = make_claim(
            "WC-AGENT-002",
            amount=5000.0,
            category=ClaimCategory.LOST_OR_STOLEN,
            description="stolen urgent cash refund",
            prior_claims=5,
            prior_claim_value=9000.0,
        )
        result = process_claim(claim.model_dump(mode="json"))

        assert result["decision"] == "escalate"

    def test_process_claim_low_risk_approves(self, make_claim):
        claim = make_claim(
            "WC-AGENT-003",
            amount=100.0,
            purchase_date=datetime.now() - timedelta(days=365),
        )
        result = process_claim(claim.model_dump(mode="json"))

        assert result["decision"] == "approve"
