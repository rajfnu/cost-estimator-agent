"""
State management for the cost estimation workflow.

Defines the shared state that flows through the LangGraph agents during
cost estimation analysis.
"""

from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass, field
from decimal import Decimal

from ..schemas import ApplicationSpecification


@dataclass
class PricingData:
    """Pricing information for a specific service or resource."""
    service: str
    provider: str
    region: str
    unit_cost: Decimal
    unit_type: str  # e.g., "per_1k_tokens", "per_hour", "per_gb_month"
    currency: str = "USD"
    last_updated: Optional[str] = None
    confidence_level: float = 1.0  # 0.0 to 1.0
    source: str = "api"  # "api", "cached", "estimated"


@dataclass
class UsageEstimate:
    """Estimated usage for a component or service."""
    component: str
    usage_amount: float
    usage_unit: str
    time_period: str = "monthly"
    confidence_level: float = 1.0
    factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostBreakdown:
    """Cost breakdown for a specific component."""
    component: str
    category: str  # e.g., "llm", "infrastructure", "storage"
    monthly_cost: Decimal
    usage_estimate: UsageEstimate
    pricing_data: PricingData
    notes: List[str] = field(default_factory=list)


@dataclass
class OptimizationSuggestion:
    """Cost optimization recommendation."""
    title: str
    description: str
    category: str
    potential_savings: Decimal
    effort_level: str  # "low", "medium", "high"
    implementation_time: str
    trade_offs: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ScenarioAnalysis:
    """Cost analysis for different scenarios."""
    scenario_name: str
    total_monthly_cost: Decimal
    cost_breakdowns: List[CostBreakdown]
    assumptions: Dict[str, Any]
    confidence_level: float = 1.0


@dataclass
class CostEstimationState:
    """
    Central state object that flows through the LangGraph agents.

    This state accumulates information and insights as it moves through
    each agent in the cost estimation workflow.
    """

    # Input data
    specification: Optional[ApplicationSpecification] = None
    raw_input: Optional[Dict[str, Any]] = None

    # Validation and enrichment
    validation_errors: List[str] = field(default_factory=list)
    enrichment_notes: List[str] = field(default_factory=list)

    # Usage pattern analysis
    usage_estimates: List[UsageEstimate] = field(default_factory=list)
    coordination_overhead: float = 0.0
    scaling_factors: Dict[str, float] = field(default_factory=dict)

    # Pricing discovery
    pricing_data: List[PricingData] = field(default_factory=list)
    pricing_issues: List[str] = field(default_factory=list)
    pricing_confidence: float = 1.0

    # Cost calculations
    cost_breakdowns: List[CostBreakdown] = field(default_factory=list)
    total_monthly_cost: Optional[Decimal] = None
    calculation_notes: List[str] = field(default_factory=list)

    # Optimization suggestions
    optimization_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    alternative_architectures: List[Dict[str, Any]] = field(default_factory=list)

    # Scenario analysis
    scenarios: List[ScenarioAnalysis] = field(default_factory=list)

    # Reporting
    executive_summary: Optional[str] = None
    detailed_report: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)

    # Metadata
    estimation_id: Optional[str] = None
    estimation_timestamp: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    agent_execution_log: List[Dict[str, Any]] = field(default_factory=list)

    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str, agent: str = "unknown") -> None:
        """Add an error with agent context."""
        self.errors.append(f"[{agent}] {error}")

    def add_warning(self, warning: str, agent: str = "unknown") -> None:
        """Add a warning with agent context."""
        self.warnings.append(f"[{agent}] {warning}")

    def log_agent_execution(self, agent: str, action: str, details: Dict[str, Any] = None) -> None:
        """Log agent execution for debugging and transparency."""
        log_entry = {
            "agent": agent,
            "action": action,
            "timestamp": None,  # Would be set by actual implementation
            "details": details or {}
        }
        self.agent_execution_log.append(log_entry)

    def get_cost_by_category(self) -> Dict[str, Decimal]:
        """Get total costs grouped by category."""
        category_costs = {}
        for breakdown in self.cost_breakdowns:
            category = breakdown.category
            if category not in category_costs:
                category_costs[category] = Decimal('0')
            category_costs[category] += breakdown.monthly_cost
        return category_costs

    def get_total_potential_savings(self) -> Decimal:
        """Calculate total potential savings from all suggestions."""
        return sum(suggestion.potential_savings for suggestion in self.optimization_suggestions)

    def has_errors(self) -> bool:
        """Check if there are any errors in the state."""
        return len(self.errors) > 0 or len(self.validation_errors) > 0

    def get_confidence_score(self) -> float:
        """Calculate overall confidence score for the estimation."""
        if not self.cost_breakdowns:
            return 0.0

        # Weight by cost breakdown confidence and pricing confidence
        total_weight = 0.0
        weighted_confidence = 0.0

        for breakdown in self.cost_breakdowns:
            weight = float(breakdown.monthly_cost)
            confidence = breakdown.usage_estimate.confidence_level * breakdown.pricing_data.confidence_level

            weighted_confidence += weight * confidence
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_confidence / total_weight