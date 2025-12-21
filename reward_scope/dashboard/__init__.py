"""
RewardScope Dashboard

FastAPI-based web dashboard for real-time RL training visualization.
"""

from .app import app, run_dashboard

__all__ = ["app", "run_dashboard"]

