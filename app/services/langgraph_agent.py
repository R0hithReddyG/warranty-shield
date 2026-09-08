"""
LangGraph Agent integration for Warranty Shield.
Implements an agentic workflow for claim processing using LangGraph.

Workflow steps:
1. Extract claim details from narrative (classification)
2. Verify product/serial existence
3. Calculate risk score (or use existing)
4. Apply additional LLM-powered narrative analysis
5. Determine final decision (approve/escalate/reject)
"""

import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.config import settings
from app.models import (
    ClaimCategory,
    WarrantyClaim,
)
from app.services import ScoringEngine

logger = logging.getLogger(__name__)


# --- State definition ---

class AgentState(TypedDict):
    """State object for the LangGraph agent workflow."""
    claim_id: str
    claim_data: dict
    risk_score: float
    risk_level: str
    events: list[dict]
    decision: str
    reason: str
    metadata: dict


# --- Tools ---

@tool
def classify_claim(description: str) -> dict:
    """Classify a claim description into a category and urgency level."""
    category = "other"
    urgency = "normal"
    desc_lower = description.lower()

    # Simple classification based on keywords
    if any(kw in desc_lower for kw in ["stolen", "lost"]):
        category = "lost_or_stolen"
        urgency = "high"
    elif any(kw in desc_lower for kw in ["accident", "drop", "crack", "break"]):
        category = "accidental_damage"
        urgency = "medium"
    elif any(kw in desc_lower for kw in ["defect", "not working", "broken"]):
        category = "defective"
        urgency = "medium"
    elif any(kw in desc_lower for kw in ["battery", "charging"]):
        category = "battery_issue"
        urgency = "low"

    return {"category": category, "urgency": urgency}


@tool
def verify_product(serial_number: str) -> dict:
    """Verify that a product exists with the given serial number."""
    # Stub: in production, this would query a product database
    if not serial_number or serial_number.strip() == "":
        return {"verified": False, "reason": "Serial number missing or empty"}
    return {"verified": True, "product_found": True, "warranty_valid": True}


@tool
def analyze_narrative(description: str, claim_id: str) -> dict:
    """
    Use LLM to analyze the claim narrative for consistency and red flags.

    Returns structured analysis including sentiment, fraud indicators,
    and suggested actions.
    """
    # Stub: in production, this would call an LLM API
    return {
        "sentiment": "neutral",
        "fraud_indicators": [],
        "suggested_action": "review",
        "confidence": 0.85,
    }


@tool
def check_prior_claims(customer_id: str) -> dict:
    """Check a customer's prior claim history."""
    # Stub: would query database in production
    return {"count": 0, "total_value": 0.0, "recent_claims": []}


# --- Node implementations ---

def extract_claim_details(state: AgentState) -> AgentState:
    """Extract and classify claim details from the narrative."""
    claim_data = state.get("claim_data", {})
    description = claim_data.get("description", "")
    events = state.get("events", [])

    result = classify_claim.invoke({"description": description})
    events.append({
        "step": "extract_claim_details",
        "event_type": "classification",
        "data": result,
    })

    return {**state, "events": events}


def verify_claim(state: AgentState) -> AgentState:
    """Verify the product and claim details."""
    claim_data = state.get("claim_data", {})
    serial = claim_data.get("product_serial", "")
    events = state.get("events", [])

    result = verify_product.invoke({"serial_number": serial})
    events.append({
        "step": "verify_claim",
        "event_type": "verification",
        "data": result,
    })

    return {**state, "events": events}


def score_claim(state: AgentState) -> AgentState:
    """Score the claim using the risk scoring engine."""
    claim_data = state.get("claim_data", {})
    events = state.get("events", [])

    # Create a WarrantyClaim from state data
    claim = _claim_from_data(claim_data, state.get("claim_id", "unknown"))

    # Score using the engine
    engine = ScoringEngine()
    result = engine.calculate_score(claim)

    events.append({
        "step": "score_claim",
        "event_type": "scoring",
        "data": {"total_score": result.total_score, "risk_level": result.risk_level},
    })

    return {
        **state,
        "risk_score": result.total_score,
        "risk_level": result.risk_level.value if result.risk_level else "low",
        "events": events,
    }


def llm_narrative_analysis(state: AgentState) -> AgentState:
    """Run LLM-powered narrative analysis."""
    claim_data = state.get("claim_data", {})
    description = claim_data.get("description", "")
    claim_id = state.get("claim_id", "unknown")
    events = state.get("events", [])

    result = analyze_narrative.invoke({
        "description": description,
        "claim_id": claim_id,
    })

    events.append({
        "step": "llm_narrative_analysis",
        "event_type": "narrative_analysis",
        "data": result,
    })

    return {**state, "events": events}


def make_decision(state: AgentState) -> AgentState:
    """Make the final decision based on risk score and analysis."""
    risk_score = state.get("risk_score", 0.0)
    events = state.get("events", [])

    # Decision logic (thresholds sourced from settings, matching the scoring engine)
    if risk_score >= settings.scoring.high_risk_threshold:
        decision = "escalate"
        reason = f"High risk score ({risk_score}) triggers escalation"
    elif risk_score >= settings.scoring.medium_risk_threshold:
        decision = "review"
        reason = f"Medium risk score ({risk_score}) requires human review"
    else:
        decision = "approve"
        reason = f"Low risk score ({risk_score}) - standard approval"

    events.append({
        "step": "make_decision",
        "event_type": "decision",
        "data": {"decision": decision, "reason": reason},
    })

    return {**state, "decision": decision, "reason": reason}


# --- Graph construction ---

def build_claim_graph() -> StateGraph:
    """
    Build the LangGraph claim processing graph.

    Graph flow:
    START -> extract_claim_details -> verify_claim -> score_claim
         -> llm_narrative_analysis -> make_decision -> END
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("extract_claim_details", extract_claim_details)
    workflow.add_node("verify_claim", verify_claim)
    workflow.add_node("score_claim", score_claim)
    workflow.add_node("llm_narrative_analysis", llm_narrative_analysis)
    workflow.add_node("make_decision", make_decision)

    # Add edges
    workflow.add_edge(START, "extract_claim_details")
    workflow.add_edge("extract_claim_details", "verify_claim")
    workflow.add_edge("verify_claim", "score_claim")
    workflow.add_edge("score_claim", "llm_narrative_analysis")
    workflow.add_edge("llm_narrative_analysis", "make_decision")
    workflow.add_edge("make_decision", END)

    return workflow


# --- Agent execution ---

def _claim_from_data(claim_data: dict, claim_id: str) -> WarrantyClaim:
    """Build a WarrantyClaim model from raw state/input data."""
    category = claim_data.get("category", ClaimCategory.OTHER.value)
    if isinstance(category, str):
        try:
            category = ClaimCategory(category.lower())
        except ValueError:
            category = ClaimCategory.OTHER

    now = datetime.now()
    purchase_date = claim_data.get("purchase_date") or now
    claim_date = claim_data.get("claim_date") or now

    return WarrantyClaim(
        claim_id=claim_id,
        product_name=claim_data.get("product_name", "Unknown"),
        product_serial=claim_data.get("product_serial", ""),
        purchase_date=purchase_date,
        claim_date=claim_date,
        category=category,
        description=claim_data.get("description", ""),
        amount=claim_data.get("amount", 1.0),
        customer_id=claim_data.get("customer_id", "unknown"),
        prior_claims=claim_data.get("prior_claims", 0),
        prior_claim_value=claim_data.get("prior_claim_value", 0.0),
    )


def process_claim(claim_data: dict) -> dict[str, Any]:
    """
    Process a warranty claim through the LangGraph agent workflow.

    Args:
        claim_data: Dictionary containing claim information

    Returns:
        Dictionary with decision, score, events, and metadata
    """
    # Only proceed if LangGraph is enabled
    if not settings.langgraph.enabled:
        logger.warning("LangGraph is disabled in settings. Skipping agent processing.")
        # Fallback to scoring engine only
        engine = ScoringEngine()
        claim = _claim_from_data(claim_data, claim_data.get("claim_id", "unknown"))
        score_result = engine.calculate_score(claim)
        if score_result.total_score >= settings.scoring.high_risk_threshold:
            decision = "escalate"
        elif score_result.total_score >= settings.scoring.medium_risk_threshold:
            decision = "review"
        else:
            decision = "approve"
        return {
            "decision": decision,
            "risk_score": score_result.total_score,
            "risk_level": score_result.risk_level.value,
            "events": [],
            "reason": f"Score-based: {score_result.risk_level.value} risk",
        }

    # Build and invoke the graph
    workflow = build_claim_graph()
    app = workflow.compile(checkpointer=MemorySaver())

    initial_state = AgentState(
        claim_id=claim_data.get("claim_id", "unknown"),
        claim_data=claim_data,
        risk_score=0.0,
        risk_level="low",
        events=[],
        decision="",
        reason="",
        metadata={},
    )

    result = app.invoke(initial_state)

    return {
        "decision": result.get("decision", "pending"),
        "risk_score": result.get("risk_score", 0.0),
        "risk_level": result.get("risk_level", "low"),
        "events": result.get("events", []),
        "reason": result.get("reason", "Agent decision pending"),
    }
