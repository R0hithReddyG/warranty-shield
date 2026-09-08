"""
Configuration module for Warranty Shield.
Handles loading and validation of application settings.
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """Database configuration."""
    path: str = Field(default="./data/warranty_shield.db", description="Path to SQLite database file")
    echo: bool = Field(default=False, description="Whether to echo SQL statements")
    connect_args: dict = Field(
        default_factory=lambda: {"check_same_thread": False},
        description="Database connection arguments"
    )


class ScoringSettings(BaseModel):
    """Risk scoring thresholds and rules."""
    high_risk_threshold: int = Field(default=70, ge=0, le=100, description="Score >= this is high risk")
    medium_risk_threshold: int = Field(default=40, ge=0, le=100, description="Score >= this is medium risk")
    early_claim_urgent_days: int = Field(default=14, ge=0, description="Days since purchase for urgent early claim")
    early_claim_watch_days: int = Field(default=30, ge=0, description="Days since purchase to watch for early claims")
    high_amount_threshold: int = Field(default=1500, ge=0, description="Amount threshold for high value claims (₹)")
    medium_amount_threshold: int = Field(default=750, ge=0, description="Amount threshold for medium value claims (₹)")
    high_prior_claims: int = Field(default=3, ge=0, description="Number of prior claims considered high risk")
    any_prior_claims: int = Field(default=1, ge=0, description="Any prior claims trigger this threshold")
    high_prior_value: int = Field(default=2000, ge=0, description="Total prior claim value threshold (₹)")
    red_flag_keywords: list[str] = Field(
        default_factory=lambda: [
            "lost", "stolen", "urgent", "cash", "refund",
            "no receipt", "discarded"
        ],
        description="Keywords that trigger red flags in narratives"
    )
    red_flag_max_score: int = Field(default=15, ge=0, description="Maximum score from red flag keywords")
    red_flag_per_match: int = Field(default=5, ge=0, description="Score per red flag keyword match")
    missing_serial_penalty: int = Field(default=8, ge=0, description="Penalty for missing serial number")
    high_risk_categories: list[str] = Field(
        default_factory=lambda: ["Lost / stolen", "Accidental damage"],
        description="Categories considered high risk"
    )


class UISettings(BaseModel):
    """Streamlit UI configuration."""
    page_title: str = Field(default="Warranty Shield", description="Browser tab title")
    page_icon: str = Field(default="🛡️", description="Browser tab icon")
    layout: str = Field(default="wide", description="Streamlit layout option")
    initial_sidebar_state: str = Field(
        default="expanded",
        description="Initial sidebar state (expanded/collapsed)"
    )


class DemoSettings(BaseModel):
    """Demo data configuration."""
    enabled: bool = Field(default=True, description="Whether demo mode is enabled")
    seed_on_empty: bool = Field(default=True, description="Whether to seed demo data on empty database")


class LangGraphSettings(BaseModel):
    """LangGraph integration settings."""
    enabled: bool = Field(default=False, description="Whether LangGraph integration is enabled")
    model: str = Field(default="claude-sonnet-4-20250514", description="LLM model to use")
    max_tokens: int = Field(default=1024, ge=1, description="Maximum tokens for LLM responses")


class AppSettings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App metadata
    name: str = Field(default="Warranty Shield", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(
        default="development",
        description="Environment (development|staging|production)"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    ui: UISettings = Field(default_factory=UISettings)
    demo: DemoSettings = Field(default_factory=DemoSettings)
    langgraph: LangGraphSettings = Field(default_factory=LangGraphSettings)

    # Security
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for security features"
    )
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts"
    )

    # Monitoring
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error tracking")
    log_level: str = Field(default="INFO", description="Logging level")


# Global settings instance
settings = AppSettings()
