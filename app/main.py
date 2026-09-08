"""
Warranty Shield — Main Application Entry Point.

Run this file to start the Streamlit UI:
    streamlit run app/main.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.ui import run_app
from app.utils import setup_logging


def main():
    """Entry point for the application."""
    logger = setup_logging(settings.log_level)
    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LangGraph enabled: {settings.langgraph.enabled}")

    run_app()


if __name__ == "__main__":
    main()
