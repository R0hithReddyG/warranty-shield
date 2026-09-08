"""
Utilities module for Warranty Shield.
Helper functions for data handling, logging, and formatting.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the application."""
    logger = logging.getLogger("warranty_shield")
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def format_currency(amount: float) -> str:
    """Format a numeric amount as Indian Rupees."""
    return f"₹{amount:,.2f}"


def format_date(dt: datetime) -> str:
    """Format a datetime object as a readable date string."""
    if dt is None:
        return "N/A"
    return dt.strftime("%d %b %Y")


def safe_json_dumps(obj: Any) -> str:
    """Serialize an object to JSON, handling datetime and other non-serializable types."""
    return json.dumps(obj, default=str, indent=2)


def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(path)


def save_csv(df: pd.DataFrame, path: str) -> None:
    """Save a DataFrame to a CSV file."""
    df.to_csv(path, index=False)


def validate_date_range(start: datetime, end: datetime) -> bool:
    """Validate that start date is before end date."""
    return start <= end


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent


def load_config_file(path: str) -> dict[str, Any]:
    """Load a YAML configuration file."""
    import yaml  # PyYAML
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def generate_claim_id() -> str:
    """Generate a unique claim ID."""
    import uuid
    return f"WC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncate a string to a maximum length, adding ellipsis if needed."""
    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def risk_level_to_color(level: str) -> str:
    """Map a risk level to a display color."""
    colors = {
        "low": "#28a745",
        "medium": "#ffc107",
        "high": "#dc3545",
        "critical": "#6f42c1",
    }
    return colors.get(level.lower(), "#6c757d")


def risk_level_to_emoji(level: str) -> str:
    """Map a risk level to an emoji indicator."""
    emojis = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
        "critical": "🟣",
    }
    return emojis.get(level.lower(), "⚪")


def compute_days_between(start: datetime, end: datetime) -> int:
    """Compute the number of days between two dates."""
    return (end - start).days


def format_risk_score(score: float) -> str:
    """Format a risk score as a percentage string."""
    return f"{score:.0f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning a default on zero division."""
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return default
