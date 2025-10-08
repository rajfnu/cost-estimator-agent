"""
AI Multi-Agent Cost Estimator

An intelligent cost estimation system for multi-agent AI applications using
LangChain and LangGraph. This agent-based solution analyzes complex AI workflows
and provides comprehensive cost breakdowns with optimization recommendations.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .api import app
from .graph import CostEstimatorGraph

__all__ = ["app", "CostEstimatorGraph", "__version__"]