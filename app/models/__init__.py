"""
Data models for Warranty Shield.
Pydantic models for validation and serialization of warranty claims.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ClaimStatus(str, Enum):
    """Possible statuses for a warranty claim."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    """Risk levels determined by the scoring engine."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClaimCategory(str, Enum):
    """Categories of warranty claims."""
    DEFECTIVE = "defective"
    ACCIDENTAL_DAMAGE = "accidental damage"
    LOST_OR_STOLEN = "lost / stolen"
    BATTERY_ISSUE = "battery issue"
    SCREEN_ISSUE = "screen issue"
    SOFTWARE_ISSUE = "software issue"
    OTHER = "other"


class WarrantyClaim(BaseModel):
    """Core model representing a warranty claim."""
    claim_id: str = Field(..., description="Unique identifier for the claim")
    product_name: str = Field(..., description="Name of the product")
    product_serial: str = Field(
        default="",
        description="Serial number of the product (required for validation)"
    )
    purchase_date: datetime = Field(..., description="Date of original purchase")
    claim_date: datetime = Field(..., description="Date the claim was filed")
    category: ClaimCategory = Field(..., description="Claim category")
    description: str = Field(..., description="Detailed description of the issue")
    amount: float = Field(..., gt=0, description="Claim amount in ₹")
    customer_id: str = Field(..., description="Customer identifier")
    prior_claims: int = Field(default=0, ge=0, description="Number of prior claims")
    prior_claim_value: float = Field(default=0.0, ge=0, description="Total value of prior claims")
    status: ClaimStatus = Field(default=ClaimStatus.PENDING, description="Current claim status")
    risk_level: RiskLevel | None = Field(default=None, description="Assessed risk level")
    risk_score: float = Field(default=0.0, ge=0, le=100, description="Numerical risk score")
    red_flags: list[str] = Field(default_factory=list, description="Detected red flag keywords")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    @field_validator("product_serial")
    @classmethod
    def validate_serial(cls, v):
        # Serial is optional; missing serials are penalized by the scoring engine.
        return v.strip() if v else ""

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v

    @field_validator("claim_date")
    @classmethod
    def validate_claim_date(cls, v, info):
        purchase = info.data.get("purchase_date")
        if purchase and v < purchase:
            raise ValueError("Claim date cannot be before purchase date")
        return v

    @property
    def days_since_purchase(self) -> int:
        """Calculate days between purchase and claim date."""
        return (self.claim_date - self.purchase_date).days

    @property
    def is_early_claim(self) -> bool:
        """Check if this is an early claim (within watch period)."""
        from app.config import settings
        return self.days_since_purchase <= settings.scoring.early_claim_watch_days

    @property
    def is_urgent_early_claim(self) -> bool:
        """Check if this is an urgent early claim (within urgent window)."""
        from app.config import settings
        return self.days_since_purchase <= settings.scoring.early_claim_urgent_days


class ScoringResult(BaseModel):
    """Result of the risk scoring calculation."""
    claim_id: str = Field(..., description="Associated claim ID")
    total_score: float = Field(..., ge=0, le=100, description="Final risk score")
    risk_level: RiskLevel = Field(..., description="Determined risk level")
    score_breakdown: dict = Field(
        default_factory=dict,
        description="Breakdown of individual score contributions"
    )
    red_flags_detected: list[str] = Field(default_factory=list, description="Keywords found")
    early_claim_bonus: float = Field(default=0.0, description="Early claim risk bonus")
    prior_claim_bonus: float = Field(default=0.0, description="Prior claim history bonus")
    amount_bonus: float = Field(default=0.0, description="High amount risk bonus")
    category_bonus: float = Field(default=0.0, description="High-risk category bonus")
    serial_missing_penalty: float = Field(default=0.0, description="Serial number missing penalty")
    narrative_penalty: float = Field(default=0.0, description="Red flag narrative penalty")
    timestamp: datetime = Field(default_factory=datetime.now, description="Scoring timestamp")

    @property
    def needs_escalation(self) -> bool:
        """Determine if the claim needs human review."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


class AgentEvent(BaseModel):
    """Event emitted by the LangGraph agent during claim processing."""
    event_type: str = Field(..., description="Type of agent event")
    claim_id: str = Field(..., description="Claim ID being processed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    data: dict = Field(default_factory=dict, description="Event-specific data")
    message: str | None = Field(default=None, description="Human-readable event message")
    step: str | None = Field(default=None, description="Agent processing step")
