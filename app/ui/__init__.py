"""
Streamlit UI for Warranty Shield.
Provides the web interface for warranty claim submission and review.
"""

from datetime import datetime

import streamlit as st

from app.config import settings
from app.models import ClaimCategory, ClaimStatus, ScoringResult, WarrantyClaim
from app.services import ScoringEngine
from app.services import service as claim_service
from app.utils import (
    format_currency,
    format_date,
    format_risk_score,
    generate_claim_id,
    risk_level_to_emoji,
)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "claims" not in st.session_state:
        st.session_state.claims = {}
    if "processed_claims" not in st.session_state:
        st.session_state.processed_claims = {}
    if "agent_events" not in st.session_state:
        st.session_state.agent_events = []
    if "claim_in_progress" not in st.session_state:
        st.session_state.claim_in_progress = False


def render_header():
    """Render the application header."""
    st.set_page_config(
        page_title=settings.ui.page_title,
        page_icon=settings.ui.page_icon,
        layout=settings.ui.layout,
        initial_sidebar_state=settings.ui.initial_sidebar_state,
    )
    st.title(f"{settings.ui.page_icon} {settings.name}")
    st.markdown(f"**Version {settings.version}** | "
                f"Environment: `{settings.environment}` | "
                f"LangGraph: `{'Enabled' if settings.langgraph.enabled else 'Disabled'}`")
    st.markdown("---")


def render_sidebar() -> dict:
    """Render the sidebar with filters and configuration."""
    st.sidebar.header("Filters & Controls")

    filter_risk = st.sidebar.multiselect(
        "Risk Level",
        options=["low", "medium", "high", "critical"],
        default=["low", "medium", "high", "critical"],
    )

    filter_status = st.sidebar.multiselect(
        "Status",
        options=["pending", "under_review", "approved", "rejected", "escalated"],
        default=["pending", "under_review", "approved", "rejected", "escalated"],
    )

    min_score = st.sidebar.slider(
        "Minimum Risk Score",
        min_value=0,
        max_value=100,
        value=0,
        help="Filter claims with score >= this value",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    total = len(st.session_state.claims)
    high_risk = sum(
        1 for c in st.session_state.claims.values()
        if c.risk_level in ("high", "critical")
    )
    st.sidebar.metric("Total Claims", total)
    st.sidebar.metric("High Risk", high_risk)
    st.sidebar.metric("LangGraph", "Active" if settings.langgraph.enabled else "Inactive")

    return {
        "risk_levels": filter_risk,
        "statuses": filter_status,
        "min_score": min_score,
    }


def render_claim_form() -> dict | None:
    """Render the claim submission form and return form data."""
    st.header("📝 Submit New Claim")

    with st.form(key="claim_form"):
        col1, col2 = st.columns(2)

        with col1:
            product_name = st.text_input("Product Name", placeholder="e.g., Laptop Pro X1")
            product_serial = st.text_input("Serial Number", placeholder="e.g., SN12345678")
            customer_id = st.text_input("Customer ID", placeholder="e.g., CUST-001")
            amount = st.number_input(
                "Claim Amount (₹)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%f",
            )
            purchase_date = st.date_input(
                "Purchase Date",
                value=datetime.now().date(),
            )
            claim_date = st.date_input(
                "Claim Date",
                value=datetime.now().date(),
            )

        with col2:
            description = st.text_area(
                "Description of Issue",
                placeholder="Describe the issue in detail...",
                height=150,
            )
            category = st.selectbox(
                "Claim Category",
                options=[c.value for c in ClaimCategory],
                index=0,
            )
            prior_claims = st.number_input(
                "Number of Prior Claims",
                min_value=0,
                value=0,
                step=1,
            )
            prior_claim_value = st.number_input(
                "Total Prior Claim Value (₹)",
                min_value=0.0,
                value=0.0,
                step=100.0,
            )

        submitted = st.form_submit_button(label="Submit Claim", use_container_width=True)

    if not submitted:
        return None

    # Basic validation
    if not product_name or not description:
        st.error("Product name and description are required.")
        return None

    if amount <= 0:
        st.error("Claim amount must be greater than zero.")
        return None

    claim_id = generate_claim_id()

    return {
        "claim_id": claim_id,
        "product_name": product_name,
        "product_serial": product_serial,
        "purchase_date": datetime.combine(purchase_date, datetime.min.time()),
        "claim_date": datetime.combine(claim_date, datetime.min.time()),
        "category": category,
        "description": description,
        "amount": float(amount),
        "customer_id": customer_id,
        "prior_claims": prior_claims,
        "prior_claim_value": float(prior_claim_value),
    }


def render_scoring_result(score_result: ScoringResult):
    """Display the risk scoring result."""
    st.markdown("### Risk Assessment")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risk Score", format_risk_score(score_result.total_score))
    with col2:
        emoji = risk_level_to_emoji(score_result.risk_level.value if score_result.risk_level else "low")
        st.metric("Risk Level", f"{emoji} {score_result.risk_level.value if score_result.risk_level else 'low'}")
    with col3:
        needs_review = "Yes" if score_result.needs_escalation else "No"
        st.metric("Needs Escalation", needs_review)

    # Score breakdown
    with st.expander("View Score Breakdown"):
        breakdown = score_result.score_breakdown
        for factor, details in breakdown.items():
            st.write(f"**{factor}:** {details}")

    if score_result.red_flags_detected:
        st.warning(f"Red flags detected: {', '.join(score_result.red_flags_detected)}")


def render_claim_table(filters: dict):
    """Render the claims table with applied filters."""
    st.header("📋 All Claims")

    claims = list(st.session_state.claims.values())

    # Apply filters
    if filters.get("risk_levels"):
        claims = [c for c in claims if c.risk_level and c.risk_level.value in filters["risk_levels"]]
    if filters.get("statuses"):
        claims = [c for c in claims if c.status.value in filters["statuses"]]
    if filters.get("min_score", 0) > 0:
        claims = [c for c in claims if c.risk_score >= filters["min_score"]]

    if not claims:
        st.info("No claims match the current filters.")
        return

    # Sort by risk score descending
    claims.sort(key=lambda c: (-c.risk_score, c.created_at))

    for claim in claims:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"**{claim.product_name}**")
                st.caption(f"ID: {claim.claim_id} | Customer: {claim.customer_id}")
            with col2:
                status_emoji = {"pending": "⏳", "under_review": "🔍", "approved": "✅", "rejected": "❌", "escalated": "🚨"}
                emoji = status_emoji.get(claim.status.value, "❓")
                st.markdown(f"{emoji} {claim.status.value}")
            with col3:
                emoji = risk_level_to_emoji(claim.risk_level.value if claim.risk_level else "low")
                st.markdown(f"{emoji} {claim.risk_level.value if claim.risk_level else 'N/A'}")
            with col4:
                st.markdown(f"💰 {format_currency(claim.amount)}")

            st.caption(f"📅 Claimed: {format_date(claim.claim_date)} | "
                       f"Days since purchase: {claim.days_since_purchase} | "
                       f"Score: {format_risk_score(claim.risk_score)}")

            if claim.red_flags:
                st.caption(f"⚠️ Red flags: {', '.join(claim.red_flags)}")


def render_claim_detail(claim_id: str):
    """Render detailed view of a specific claim."""
    claim = st.session_state.claims.get(claim_id)
    if not claim:
        st.error("Claim not found.")
        return

    st.header(f"Claim Details: {claim.claim_id}")

    # Display claim info in columns
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Product:**", claim.product_name)
        st.write("**Serial:**", claim.product_serial)
        st.write("**Customer:**", claim.customer_id)
        st.write("**Amount:**", format_currency(claim.amount))
    with col2:
        st.write("**Category:**", claim.category)
        st.write("**Purchase Date:**", format_date(claim.purchase_date))
        st.write("**Claim Date:**", format_date(claim.claim_date))
        st.write("**Days Since Purchase:**", claim.days_since_purchase)

    st.write("**Description:**", claim.description)

    # Show score breakdown
    st.markdown("### Risk Score Breakdown")
    engine = ScoringEngine()
    result = engine.calculate_score(claim)
    render_scoring_result(result)

    # Status actions
    st.markdown("### Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Approve", key=f"approve_{claim_id}"):
            claim.status = ClaimStatus.APPROVED
            claim.updated_at = datetime.now()
            st.rerun()
    with col2:
        if st.button("Reject", key=f"reject_{claim_id}"):
            claim.status = ClaimStatus.REJECTED
            claim.updated_at = datetime.now()
            st.rerun()
    with col3:
        if st.button("Escalate", key=f"escalate_{claim_id}"):
            claim.status = ClaimStatus.ESCALATED
            claim.updated_at = datetime.now()
            st.rerun()


def render_agent_events():
    """Render the agent events log."""
    st.header("🤖 Agent Events Log")
    if not st.session_state.agent_events:
        st.info("No agent events recorded yet.")
        return

    for event in reversed(st.session_state.agent_events):
        with st.expander(
            f"[{event.get('event_type', 'unknown')}] "
            f"Claim: {event.get('claim_id', 'N/A')} | "
            f"Step: {event.get('step', 'N/A')}"
        ):
            st.json(event.get("data", {}))


def run_app():
    """Run the Streamlit application."""
    initialize_session_state()
    render_header()

    filters = render_sidebar()

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["Submit Claim", "Claim Review", "Agent Events"])

    with tab1:
        form_data = render_claim_form()
        if form_data:
            # Create the claim via service
            claim = WarrantyClaim(**form_data)
            result = claim_service.create_claim(claim)
            st.session_state.claims[result.claim_id] = result
            st.success(f"Claim submitted successfully! ID: {result.claim_id}")

            # Calculate and display risk score
            engine = ScoringEngine()
            score_result = engine.calculate_score(result)
            render_scoring_result(score_result)

            st.session_state.claim_in_progress = True

    with tab2:
        if not st.session_state.claims:
            st.info("No claims submitted yet. Go to the Submit Claim tab.")
        else:
            render_claim_table(filters)

    with tab3:
        render_agent_events()

    # Footer
    st.markdown("---")
    st.caption("Warranty Shield — Explainable warranty-claim risk triage with LangGraph integration")
