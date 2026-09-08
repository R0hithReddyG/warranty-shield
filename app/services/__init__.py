"""
Services module for Warranty Shield.
Contains business logic for risk scoring, claim processing, and LangGraph agent integration.
"""

import re
from datetime import datetime

from app.config import settings
from app.models import (
    AgentEvent,
    ClaimCategory,
    ClaimStatus,
    RiskLevel,
    ScoringResult,
    WarrantyClaim,
)


class ScoringEngine:
    """
    Risk scoring engine for warranty claims.

    Calculates a comprehensive risk score based on multiple factors:
    - Claim amount thresholds
    - Prior claim history
    - Category risk
    - Early claim windows
    - Red flag keywords in narrative
    - Missing serial number penalty
    """

    HIGH_RISK_CATEGORY_SCORE = 20.0
    LOW_RISK_CATEGORY_SCORE = 5.0

    def __init__(self):
        self._score_breakdown: dict = {}

    def calculate_score(self, claim: WarrantyClaim) -> ScoringResult:
        """
        Calculate the overall risk score for a warranty claim.

        The score is calculated from multiple weighted components:
        - Base score from amount thresholds (0-40 points)
        - Prior claim history bonus (0-25 points)
        - Category risk bonus (0-20 points)
        - Early claim penalty (0-10 points)
        - Red flag keyword penalties (0-20 points, max 15)
        - Missing serial number penalty (0-8 points)
        """
        self._score_breakdown = {}
        total_score = 0.0

        # 1. Amount-based scoring (0-40 points)
        amount_score = self._score_amount(claim.amount)
        total_score += amount_score
        self._score_breakdown["amount"] = {
            "raw_amount": claim.amount,
            "score": amount_score,
            "description": "Based on claim amount thresholds",
        }

        # 2. Prior claim history (0-25 points)
        prior_score = self._score_prior_claims(claim.prior_claims, claim.prior_claim_value)
        total_score += prior_score
        self._score_breakdown["prior_claims"] = {
            "count": claim.prior_claims,
            "total_value": claim.prior_claim_value,
            "score": prior_score,
            "description": "Based on previous claim history",
        }

        # 3. Category risk (0-20 points)
        category_score = self._score_category(claim.category)
        total_score += category_score
        self._score_breakdown["category"] = {
            "category": claim.category,
            "score": category_score,
            "description": "Based on claim category risk level",
        }

        # 4. Early claim penalty (0-10 points)
        early_score = self._score_early_claim(claim.days_since_purchase)
        total_score += early_score
        self._score_breakdown["early_claim"] = {
            "days_since_purchase": claim.days_since_purchase,
            "score": early_score,
            "description": "Penalty for claims filed early after purchase",
        }

        # 5. Red flag keywords (0-15 points max, 5 points per match)
        red_flag_score, detected_flags = self._score_red_flags(claim.description)
        total_score += red_flag_score
        self._score_breakdown["red_flags"] = {
            "flags": detected_flags,
            "score": red_flag_score,
            "description": "Keywords indicating urgency or suspicious circumstances",
        }

        # 6. Missing serial number penalty (0-8 points)
        serial_penalty = self._score_missing_serial(claim.product_serial)
        total_score += serial_penalty
        self._score_breakdown["missing_serial"] = {
            "serial": claim.product_serial[:20] if claim.product_serial else "(empty)",
            "penalty": serial_penalty,
            "description": "Penalty for missing product serial number",
        }

        # 7. Categorize risk level
        risk_level = self._classify_risk(total_score)

        # 8. Apply category bonuses/additional adjustments
        red_flags_detected = self._score_breakdown.get("red_flags", {}).get("flags", [])

        return ScoringResult(
            claim_id=claim.claim_id,
            total_score=min(total_score, 100.0),
            risk_level=risk_level,
            score_breakdown=self._score_breakdown,
            red_flags_detected=red_flags_detected,
            early_claim_bonus=self._score_breakdown.get("early_claim", {}).get("score", 0),
            prior_claim_bonus=self._score_breakdown.get("prior_claims", {}).get("score", 0),
            amount_bonus=self._score_breakdown.get("amount", {}).get("score", 0),
            category_bonus=self._score_breakdown.get("category", {}).get("score", 0),
            serial_missing_penalty=self._score_breakdown.get("missing_serial", {}).get("penalty", 0),
            narrative_penalty=self._score_breakdown.get("red_flags", {}).get("score", 0),
        )

    def _score_amount(self, amount: float) -> float:
        """Score based on claim amount thresholds."""
        if amount >= settings.scoring.high_amount_threshold:
            return 40.0
        elif amount >= settings.scoring.medium_amount_threshold:
            return 25.0
        elif amount > 0:
            return 10.0
        return 0.0

    def _score_prior_claims(self, count: int, total_value: float) -> float:
        """Score based on prior claim history."""
        score = 0.0
        # Base score for any prior claims
        if count >= settings.scoring.high_prior_claims:
            score = 25.0
        elif count >= settings.scoring.any_prior_claims:
            score = 10.0
        # If total prior value is very high, add bonus
        if total_value >= settings.scoring.high_prior_value:
            score = min(score + 10.0, 25.0)
        return score

    def _score_category(self, category: ClaimCategory) -> float:
        """Score based on claim category risk level."""
        high_risk = settings.scoring.high_risk_categories
        # Check if category is in high risk list (case-insensitive match)
        category_str = category.value.lower()
        if any(hr_cat.lower() in category_str for hr_cat in high_risk):
            return self.HIGH_RISK_CATEGORY_SCORE
        return self.LOW_RISK_CATEGORY_SCORE  # Low-medium risk category

    def _score_early_claim(self, days_since_purchase: int) -> float:
        """Score based on how early the claim is filed after purchase."""
        if days_since_purchase <= 0:
            return 10.0  # Very suspicious - claim filed same day or before purchase
        elif days_since_purchase <= settings.scoring.early_claim_urgent_days:
            return 10.0  # Urgent early claim window
        elif days_since_purchase <= settings.scoring.early_claim_watch_days:
            return 5.0  # Watch window
        return 0.0  # Normal claim timing

    def _score_red_flags(self, description: str) -> tuple:
        """
        Score based on red flag keywords in the claim description.

        Returns:
            (score, list_of_matched_keywords)
        """
        detected = []
        description_lower = description.lower() if description else ""
        score = 0.0

        for keyword in settings.scoring.red_flag_keywords:
            # Case-insensitive word boundary match
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, description_lower):
                detected.append(keyword)
                score += settings.scoring.red_flag_per_match

        # Cap at max score
        score = min(score, settings.scoring.red_flag_max_score)
        return score, detected

    def _score_missing_serial(self, serial: str) -> float:
        """Penalty for missing product serial number."""
        if not serial or serial.strip() == "":
            return float(settings.scoring.missing_serial_penalty)
        return 0.0

    def _classify_risk(self, score: float) -> RiskLevel:
        """Classify the risk level based on total score.

        The engine maps scores to LOW / MEDIUM / HIGH; CRITICAL is reserved
        for manual designation by reviewers via the ClaimService.
        """
        if score >= settings.scoring.high_risk_threshold:
            return RiskLevel.HIGH
        elif score >= settings.scoring.medium_risk_threshold:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class ClaimService:
    """
    Service layer for managing warranty claims lifecycle.
    Handles claim creation, status updates, and score recomputation.
    """

    def __init__(self):
        self._scoring_engine = ScoringEngine()
        self._claims: dict[str, WarrantyClaim] = {}

    def create_claim(self, claim: WarrantyClaim) -> WarrantyClaim:
        """Create a new claim and compute its initial risk score."""
        claim.risk_level = None
        claim.risk_score = 0.0
        claim.status = ClaimStatus.PENDING
        claim.created_at = datetime.now()
        claim.updated_at = datetime.now()

        # Calculate initial risk score
        result = self._scoring_engine.calculate_score(claim)
        claim.risk_score = result.total_score
        claim.risk_level = result.risk_level
        claim.red_flags = result.red_flags_detected
        claim.updated_at = datetime.now()

        self._claims[claim.claim_id] = claim
        return claim

    def update_status(self, claim_id: str, new_status: ClaimStatus) -> WarrantyClaim | None:
        """Update claim status."""
        claim = self._claims.get(claim_id)
        if claim:
            claim.status = new_status
            claim.updated_at = datetime.now()
        return claim

    def recompute_score(self, claim_id: str) -> ScoringResult | None:
        """Recompute risk score for an existing claim."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None
        result = self._scoring_engine.calculate_score(claim)
        claim.risk_score = result.total_score
        claim.risk_level = result.risk_level
        claim.red_flags = result.red_flags_detected
        claim.updated_at = datetime.now()
        return result

    def get_claim(self, claim_id: str) -> WarrantyClaim | None:
        """Get a claim by ID."""
        return self._claims.get(claim_id)

    def list_claims(
        self,
        status: ClaimStatus | None = None,
        risk_level: RiskLevel | None = None,
        risk_threshold: float = 0.0,
    ) -> list[WarrantyClaim]:
        """List claims with optional filtering."""
        claims = list(self._claims.values())

        if status:
            claims = [c for c in claims if c.status == status]
        if risk_level:
            claims = [c for c in claims if c.risk_level == risk_level]
        if risk_threshold > 0:
            claims = [c for c in claims if c.risk_score >= risk_threshold]

        # Sort by risk score descending, then by creation date
        claims.sort(key=lambda c: (-c.risk_score, c.created_at))
        return claims

    def get_escalated_claims(self) -> list[WarrantyClaim]:
        """Get all claims that need human/escalation review."""
        return [
            c for c in self._claims.values()
            if c.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]

    def emit_agent_event(
        self,
        event_type: str,
        claim_id: str,
        data: dict | None = None,
        message: str | None = None,
        step: str | None = None,
    ) -> AgentEvent:
        """Emit an agent event during LangGraph processing."""
        event = AgentEvent(
            event_type=event_type,
            claim_id=claim_id,
            data=data or {},
            message=message,
            step=step,
        )
        # In a real system, this would publish to a message queue
        return event


# Global service instance
service = ClaimService()
