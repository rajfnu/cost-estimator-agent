"""
FastAPI-based REST API for the Cost Estimator Agent.

Provides a modern REST API interface for cost estimation services,
enabling integration with web applications and other systems.
"""

from .app import app, get_health

__all__ = ["app", "get_health"]