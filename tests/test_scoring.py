"""
Tests for the risk scoring engine.
"""

from datetime import datetime, timedelta

import pytest

from app.config import settings
from app.models import ClaimCategory, WarrantyClaim
from app.services import ScoringEngine


@pytest.fixture
def sample_claim():
    """Create a sample warranty claim for testing."""
    return WarrantyClaim(
        claim_id="WC-TEST-001",
        product_name="Test Product",
        product_serial="SN12345678",
        purchase_date=datetime.now() - timedelta(days=60),
        claim_date=datetime.now(),
        category=ClaimCategory.DEFECTIVE,
        description="Product is not working properly",
        amount=1000.0,
        customer_id="CUST-001",
        prior_claims=0,
        prior_claim_value=0.0,
    )


@pytest.fixture
def scoring_engine():
    """Create a scoring engine instance."""
    return ScoringEngine()


class TestScoringEngine:
    """Tests for the ScoringEngine class."""

    def test_basic_scoring(self, sample_claim, scoring_engine):
        """Test basic scoring with a simple claim."""
        result = scoring_engine.calculate_score(sample_claim)

        assert result.claim_id == "WC-TEST-001"
        assert result.total_score >= 0
        assert result.total_score <= 100
        assert result.risk_level is not None

    def test_high_amount_scores_high_risk(self, scoring_engine):
        """Test that high claim amounts increase risk score."""
        high_amount_claim = WarrantyClaim(
            claim_id="WC-HIGH-001",
            product_name="Expensive Product",
            product_serial="SN99999999",
            purchase_date=datetime.now() - timedelta(days=365),
            claim_date=datetime.now(),
            category=ClaimCategory.DEFECTIVE,
            description="Broken screen",
            amount=5000.0,
            customer_id="CUST-002",
        )
        result = scoring_engine.calculate_score(high_amount_claim)
        assert result.amount_bonus >= 25.0

    def test_red_flag_keywords_increase_score(self, scoring_engine):
        """Test that red flag keywords in narrative increase score."""
        red_flag_claim = WarrantyClaim(
            claim_id="WC-RED-001",
            product_name="Test Product",
            product_serial="SN11111111",
            purchase_date=datetime.now() - timedelta(days=30),
            claim_date=datetime.now(),
            category=ClaimCategory.DEFECTIVE,
            description="urgent need for cash refund, no receipt",
            amount=500.0,
            customer_id="CUST-003",
        )
        result = scoring_engine.calculate_score(red_flag_claim)
        assert result.narrative_penalty > 0
        assert len(result.red_flags_detected) > 0

    def test_missing_serial_penalty(self, scoring_engine):
        """Test that missing serial number adds penalty."""
        no_serial_claim = WarrantyClaim(
            claim_id="WC-NOSERIAL-001",
            product_name="Test Product",
            product_serial="",  # Missing serial
            purchase_date=datetime.now() - timedelta(days=30),
            claim_date=datetime.now(),
            category=ClaimCategory.DEFECTIVE,
            description="Defective product",
            amount=500.0,
            customer_id="CUST-004",
        )
        result = scoring_engine.calculate_score(no_serial_claim)
        assert result.serial_missing_penalty > 0

    def test_prior_claims_bonus(self, scoring_engine):
        """Test that prior claims increase risk score."""
        repeat_claim = WarrantyClaim(
            claim_id="WC-REPEAT-001",
            product_name="Test Product",
            product_serial="SN22222222",
            purchase_date=datetime.now() - timedelta(days=180),
            claim_date=datetime.now(),
            category=ClaimCategory.DEFECTIVE,
            description="Still broken after repair",
            amount=800.0,
            customer_id="CUST-005",
            prior_claims=5,
            prior_claim_value=3000.0,
        )
        result = scoring_engine.calculate_score(repeat_claim)
        assert result.prior_claim_bonus > 0

    def test_early_claim_penalty(self, scoring_engine):
        """Test that early claims get penalty."""
        early_claim = WarrantyClaim(
            claim_id="WC-EARLY-001",
            product_name="Test Product",
            product_serial="SN33333333",
            purchase_date=datetime.now() - timedelta(days=5),
            claim_date=datetime.now(),
            category=ClaimCategory.DEFECTIVE,
            description="Not working",
            amount=500.0,
            customer_id="CUST-006",
        )
        result = scoring_engine.calculate_score(early_claim)
        assert result.early_claim_bonus > 0

    def test_critical_risk_classification(self, scoring_engine):
        """Test that very high scores are classified as critical."""
        critical_claim = WarrantyClaim(
            claim_id="WC-CRITICAL-001",
            product_name="Test Product",
            product_serial="SN44444444",
            purchase_date=datetime.now() - timedelta(days=5),
            claim_date=datetime.now(),
            category=ClaimCategory.LOST_OR_STOLEN,
            description="stolen and urgent cash refund needed",
            amount=5000.0,
            customer_id="CUST-007",
            prior_claims=5,
            prior_claim_value=10000.0,
        )
        result = scoring_engine.calculate_score(critical_claim)
        assert result.total_score >= settings.scoring.high_risk_threshold
        assert result.risk_level.value == "high"

    def test_score_breakdown_not_empty(self, sample_claim, scoring_engine):
        """Test that the score breakdown contains expected keys."""
        result = scoring_engine.calculate_score(sample_claim)
        breakdown = result.score_breakdown

        assert "amount" in breakdown
        assert "prior_claims" in breakdown
        assert "category" in breakdown
        assert "early_claim" in breakdown
        assert "red_flags" in breakdown
        assert "missing_serial" in breakdown

    def test_needs_escalation(self, scoring_engine):
        """Test that high-risk claims need escalation."""
        high_claim = WarrantyClaim(
            claim_id="WC-ESCALATE-001",
            product_name="Test Product",
            product_serial="SN55555555",
            purchase_date=datetime.now() - timedelta(days=1),
            claim_date=datetime.now(),
            category=ClaimCategory.LOST_OR_STOLEN,
            description="stolen urgent cash refund",
            amount=3000.0,
            customer_id="CUST-008",
            prior_claims=3,
            prior_claim_value=5000.0,
        )
        result = scoring_engine.calculate_score(high_claim)
        assert result.needs_escalation is True
