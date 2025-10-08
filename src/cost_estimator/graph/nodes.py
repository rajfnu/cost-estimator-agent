"""
Individual agent nodes for the cost estimation workflow.

Each agent is specialized for a specific aspect of cost estimation,
following the principle of separation of concerns while enabling
intelligent reasoning about costs.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.schema.runnable import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from ..schemas import ApplicationSpecification, ComplexityLevel
from .state import CostEstimationState, UsageEstimate, PricingData, CostBreakdown, OptimizationSuggestion

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all cost estimation agents."""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,
            max_tokens=2000
        )

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Invoke the agent with the current state."""
        raise NotImplementedError("Subclasses must implement invoke method")

    def _create_system_message(self, content: str) -> SystemMessage:
        """Create a system message for LLM interaction."""
        return SystemMessage(content=content)

    def _create_human_message(self, content: str) -> HumanMessage:
        """Create a human message for LLM interaction."""
        return HumanMessage(content=content)


class InputParserAgent(BaseAgent):
    """
    Validates and enriches application specifications.

    This agent ensures the input data is valid, complete, and enriched
    with intelligent defaults based on application patterns.
    """

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Parse and validate the input specification."""
        state.log_agent_execution("InputParserAgent", "starting_validation")

        try:
            # Parse and validate the specification
            if state.raw_input and not state.specification:
                state.specification = ApplicationSpecification(**state.raw_input)

            if not state.specification:
                state.add_error("No specification provided", "InputParserAgent")
                return state

            # Enrich the specification with intelligent defaults
            await self._enrich_specification(state)

            # Validate business logic
            self._validate_business_rules(state)

            state.log_agent_execution("InputParserAgent", "validation_complete", {
                "errors": len(state.validation_errors),
                "enrichments": len(state.enrichment_notes)
            })

        except ValidationError as e:
            for error in e.errors():
                state.validation_errors.append(f"Validation error: {error['msg']} at {error['loc']}")
        except Exception as e:
            state.add_error(f"Unexpected error during validation: {str(e)}", "InputParserAgent")

        return state

    async def _enrich_specification(self, state: CostEstimationState) -> None:
        """Use LLM to enrich specification with intelligent defaults."""
        spec = state.specification

        # Prepare context for LLM
        system_prompt = """
        You are an expert in multi-agent AI application architecture and cost modeling.
        Analyze the provided application specification and suggest intelligent defaults
        or improvements based on industry best practices.

        Focus on:
        1. Realistic usage patterns based on application type
        2. Appropriate infrastructure sizing
        3. Missing but important configurations
        4. Industry-specific considerations

        Respond with specific, actionable suggestions in JSON format.
        """

        human_prompt = f"""
        Application Specification:
        {spec.dict()}

        Please analyze this specification and provide suggestions for:
        1. Usage pattern refinements
        2. Infrastructure optimizations
        3. Missing configurations
        4. Industry best practices

        Format your response as JSON with clear reasoning.
        """

        try:
            messages = [
                self._create_system_message(system_prompt),
                self._create_human_message(human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            # Process LLM response and apply enrichments
            state.enrichment_notes.append(f"LLM enrichment suggestions: {response.content}")

        except Exception as e:
            state.add_warning(f"Could not enrich specification: {str(e)}", "InputParserAgent")

    def _validate_business_rules(self, state: CostEstimationState) -> None:
        """Validate business logic and consistency."""
        spec = state.specification

        # Check for reasonable user counts vs infrastructure
        if spec.application.expected_users > 10000 and not any(
            agent.complexity in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL]
            for agent in spec.agents
        ):
            state.add_warning(
                "High user count with low complexity agents may need review",
                "InputParserAgent"
            )

        # Validate availability requirements
        if spec.infrastructure.availability_requirement > 99.9 and \
           spec.infrastructure.availability_zones < 3:
            state.add_warning(
                "High availability requirement should use at least 3 availability zones",
                "InputParserAgent"
            )


class UsagePatternAnalyzer(BaseAgent):
    """
    Analyzes workflow complexity and predicts realistic usage patterns.

    This agent goes beyond simple multiplication of averages to model
    realistic usage patterns based on application complexity and user behavior.
    """

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Analyze usage patterns and create realistic estimates."""
        state.log_agent_execution("UsagePatternAnalyzer", "starting_analysis")

        if not state.specification:
            state.add_error("No specification available for analysis", "UsagePatternAnalyzer")
            return state

        try:
            # Analyze each agent's usage patterns
            for agent_config in state.specification.agents:
                await self._analyze_agent_usage(state, agent_config)

            # Calculate coordination overhead
            self._calculate_coordination_overhead(state)

            # Analyze scaling factors
            self._analyze_scaling_factors(state)

            state.log_agent_execution("UsagePatternAnalyzer", "analysis_complete", {
                "usage_estimates": len(state.usage_estimates),
                "coordination_overhead": state.coordination_overhead
            })

        except Exception as e:
            state.add_error(f"Error during usage analysis: {str(e)}", "UsagePatternAnalyzer")

        return state

    async def _analyze_agent_usage(self, state: CostEstimationState, agent_config) -> None:
        """Analyze usage patterns for a specific agent using LLM reasoning."""
        system_prompt = """
        You are an expert in AI agent usage pattern analysis. Given an agent configuration
        and application context, estimate realistic token usage, API calls, and resource
        utilization patterns.

        Consider factors like:
        - Agent complexity and role
        - Interaction frequency
        - Tool usage patterns
        - Multi-agent coordination overhead
        - Real-world usage variability

        Provide specific, quantified estimates with reasoning.
        """

        agent_context = f"""
        Agent: {agent_config.name}
        Role: {agent_config.role}
        Complexity: {agent_config.complexity}
        Interaction Frequency: {agent_config.interaction_frequency}
        LLM Model: {agent_config.llm_config.name}
        Tools: {[tool.name for tool in agent_config.tools]}

        Application Context:
        - Users: {state.specification.application.expected_users}
        - Sessions per user/month: {state.specification.application.usage_patterns.sessions_per_user_month}
        - Session duration: {state.specification.application.usage_patterns.avg_session_duration_minutes} minutes

        Estimate monthly token usage, considering realistic conversation patterns and agent complexity.
        """

        try:
            messages = [
                self._create_system_message(system_prompt),
                self._create_human_message(agent_context)
            ]

            response = await self.llm.ainvoke(messages)

            # For now, create a basic estimate (would parse LLM response in full implementation)
            estimated_tokens = self._calculate_base_token_usage(state, agent_config)

            usage_estimate = UsageEstimate(
                component=f"{agent_config.name}_tokens",
                usage_amount=estimated_tokens,
                usage_unit="tokens",
                confidence_level=0.8,
                factors={
                    "complexity_multiplier": self._get_complexity_multiplier(agent_config.complexity),
                    "interaction_frequency": agent_config.interaction_frequency,
                    "llm_reasoning": response.content[:200] + "..."
                }
            )
            state.usage_estimates.append(usage_estimate)

        except Exception as e:
            state.add_warning(f"Could not analyze usage for {agent_config.name}: {str(e)}", "UsagePatternAnalyzer")

    def _calculate_base_token_usage(self, state: CostEstimationState, agent_config) -> float:
        """Calculate base token usage with intelligent estimation."""
        app = state.specification.application
        usage_patterns = app.usage_patterns

        # Base calculation
        monthly_sessions = app.expected_users * usage_patterns.sessions_per_user_month

        # Estimate tokens per session based on agent complexity and session duration
        base_tokens_per_session = usage_patterns.avg_session_duration_minutes * 100  # ~100 tokens per minute

        # Apply complexity multiplier
        complexity_multiplier = self._get_complexity_multiplier(agent_config.complexity)
        tokens_per_session = base_tokens_per_session * complexity_multiplier

        # Apply interaction frequency multiplier
        frequency_multiplier = {
            "on_demand": 0.3,
            "periodic": 0.6,
            "continuous": 1.0
        }.get(agent_config.interaction_frequency, 1.0)

        # Calculate monthly tokens
        monthly_tokens = monthly_sessions * tokens_per_session * frequency_multiplier

        # Apply coordination overhead for multi-agent scenarios
        if len(state.specification.agents) > 1:
            monthly_tokens *= (1 + agent_config.coordination_overhead)

        return monthly_tokens

    def _get_complexity_multiplier(self, complexity: ComplexityLevel) -> float:
        """Get multiplier based on complexity level."""
        multipliers = {
            ComplexityLevel.LOW: 0.5,
            ComplexityLevel.MEDIUM: 1.0,
            ComplexityLevel.HIGH: 2.0,
            ComplexityLevel.CRITICAL: 3.5
        }
        return multipliers.get(complexity, 1.0)

    def _calculate_coordination_overhead(self, state: CostEstimationState) -> None:
        """Calculate overhead from multi-agent coordination."""
        agent_count = len(state.specification.agents)
        if agent_count <= 1:
            state.coordination_overhead = 0.0
            return

        # Base overhead increases with agent count
        base_overhead = 0.1 * (agent_count - 1)

        # Adjust based on complexity
        high_complexity_agents = sum(
            1 for agent in state.specification.agents
            if agent.complexity in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL]
        )

        complexity_factor = 1 + (high_complexity_agents * 0.2)
        state.coordination_overhead = base_overhead * complexity_factor

    def _analyze_scaling_factors(self, state: CostEstimationState) -> None:
        """Analyze how costs scale with usage."""
        usage_patterns = state.specification.application.usage_patterns

        state.scaling_factors = {
            "user_growth": 1 + usage_patterns.growth_rate_monthly,
            "seasonal_variance": 1 + usage_patterns.seasonal_variance,
            "peak_concurrency": usage_patterns.peak_concurrency_ratio,
            "retention_impact": usage_patterns.retention_rate
        }


class CostDiscoveryAgent(BaseAgent):
    """
    Fetches live pricing data and maintains cached fallbacks.

    This agent handles the complexity of retrieving accurate, up-to-date
    pricing information from various providers while gracefully handling
    failures with cached data.
    """

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        super().__init__(llm)
        self.pricing_cache = {}  # In production, this would be a proper cache

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Discover and cache pricing data for all required services."""
        state.log_agent_execution("CostDiscoveryAgent", "starting_price_discovery")

        if not state.specification:
            state.add_error("No specification available for pricing", "CostDiscoveryAgent")
            return state

        try:
            # Discover pricing for LLM services
            await self._discover_llm_pricing(state)

            # Discover pricing for cloud infrastructure
            await self._discover_infrastructure_pricing(state)

            # Discover pricing for vector databases
            await self._discover_vector_db_pricing(state)

            # Calculate overall pricing confidence
            self._calculate_pricing_confidence(state)

            state.log_agent_execution("CostDiscoveryAgent", "price_discovery_complete", {
                "pricing_entries": len(state.pricing_data),
                "confidence": state.pricing_confidence
            })

        except Exception as e:
            state.add_error(f"Error during price discovery: {str(e)}", "CostDiscoveryAgent")

        return state

    async def _discover_llm_pricing(self, state: CostEstimationState) -> None:
        """Discover pricing for LLM services."""
        for agent_config in state.specification.agents:
            llm_config = agent_config.llm_config

            try:
                # In a real implementation, this would call live APIs
                pricing = await self._get_llm_pricing(llm_config.provider, llm_config.name)
                state.pricing_data.append(pricing)
            except Exception as e:
                # Fall back to cached/estimated pricing
                fallback_pricing = self._get_fallback_llm_pricing(llm_config.provider, llm_config.name)
                state.pricing_data.append(fallback_pricing)
                state.pricing_issues.append(f"Using fallback pricing for {llm_config.name}: {str(e)}")

    async def _get_llm_pricing(self, provider: str, model: str) -> PricingData:
        """Get live LLM pricing (placeholder implementation)."""
        # This would integrate with actual pricing APIs
        pricing_map = {
            ("openai", "gpt-4-turbo"): (0.01, 0.03),
            ("openai", "gpt-3.5-turbo"): (0.001, 0.002),
            ("anthropic", "claude-3-opus"): (0.015, 0.075),
            ("anthropic", "claude-3-sonnet"): (0.003, 0.015),
        }

        input_cost, output_cost = pricing_map.get((provider, model), (0.01, 0.03))

        return PricingData(
            service=f"{provider}_{model}",
            provider=provider,
            region="global",
            unit_cost=Decimal(str(input_cost)),
            unit_type="per_1k_input_tokens",
            last_updated=datetime.now().isoformat(),
            confidence_level=0.95,
            source="api"
        )

    def _get_fallback_llm_pricing(self, provider: str, model: str) -> PricingData:
        """Get fallback pricing when live pricing fails."""
        # Generic fallback pricing
        return PricingData(
            service=f"{provider}_{model}",
            provider=provider,
            region="global",
            unit_cost=Decimal("0.01"),
            unit_type="per_1k_input_tokens",
            confidence_level=0.6,
            source="cached"
        )

    async def _discover_infrastructure_pricing(self, state: CostEstimationState) -> None:
        """Discover pricing for cloud infrastructure."""
        cloud_provider = state.specification.infrastructure.cloud_provider
        region = state.specification.infrastructure.region

        # Placeholder infrastructure pricing discovery
        # In reality, this would integrate with AWS/Azure/GCP pricing APIs
        pricing = PricingData(
            service="compute_instance",
            provider=cloud_provider,
            region=region,
            unit_cost=Decimal("0.10"),
            unit_type="per_hour",
            confidence_level=0.8,
            source="estimated"
        )
        state.pricing_data.append(pricing)

    async def _discover_vector_db_pricing(self, state: CostEstimationState) -> None:
        """Discover pricing for vector database services."""
        for vector_config in state.specification.data_requirements.vector_stores:
            pricing = PricingData(
                service=f"vector_db_{vector_config.provider}",
                provider=vector_config.provider,
                region="global",
                unit_cost=Decimal("0.70"),
                unit_type="per_gb_month",
                confidence_level=0.7,
                source="estimated"
            )
            state.pricing_data.append(pricing)

    def _calculate_pricing_confidence(self, state: CostEstimationState) -> None:
        """Calculate overall confidence in pricing data."""
        if not state.pricing_data:
            state.pricing_confidence = 0.0
            return

        total_confidence = sum(pricing.confidence_level for pricing in state.pricing_data)
        state.pricing_confidence = total_confidence / len(state.pricing_data)


class CalculationEngineAgent(BaseAgent):
    """
    Computes costs with interdependency awareness and scaling behavior.

    This agent combines usage estimates with pricing data to calculate
    realistic costs, considering how components interact and affect each other.
    """

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Calculate comprehensive costs with interdependency modeling."""
        state.log_agent_execution("CalculationEngineAgent", "starting_calculations")

        if not state.usage_estimates or not state.pricing_data:
            state.add_error("Missing usage estimates or pricing data", "CalculationEngineAgent")
            return state

        try:
            # Calculate LLM costs
            await self._calculate_llm_costs(state)

            # Calculate infrastructure costs
            await self._calculate_infrastructure_costs(state)

            # Calculate storage and data costs
            await self._calculate_storage_costs(state)

            # Apply interdependency adjustments
            self._apply_interdependency_adjustments(state)

            # Calculate total costs
            self._calculate_total_costs(state)

            state.log_agent_execution("CalculationEngineAgent", "calculations_complete", {
                "cost_breakdowns": len(state.cost_breakdowns),
                "total_cost": float(state.total_monthly_cost) if state.total_monthly_cost else 0
            })

        except Exception as e:
            state.add_error(f"Error during cost calculation: {str(e)}", "CalculationEngineAgent")

        return state

    async def _calculate_llm_costs(self, state: CostEstimationState) -> None:
        """Calculate LLM-related costs."""
        for usage_estimate in state.usage_estimates:
            if "_tokens" in usage_estimate.component:
                # Find corresponding pricing data
                agent_name = usage_estimate.component.replace("_tokens", "")

                # Find the agent configuration
                agent_config = next(
                    (agent for agent in state.specification.agents if agent.name == agent_name),
                    None
                )

                if not agent_config:
                    continue

                # Find pricing data for this LLM
                llm_provider = agent_config.llm_config.provider
                pricing_data = next(
                    (pricing for pricing in state.pricing_data if pricing.provider == llm_provider),
                    None
                )

                if pricing_data:
                    # Calculate monthly cost
                    tokens_per_month = usage_estimate.usage_amount
                    cost_per_1k_tokens = pricing_data.unit_cost
                    monthly_cost = (tokens_per_month / 1000) * cost_per_1k_tokens

                    # Apply scaling factors
                    scaling_multiplier = state.scaling_factors.get("user_growth", 1.0)
                    monthly_cost *= scaling_multiplier

                    cost_breakdown = CostBreakdown(
                        component=usage_estimate.component,
                        category="llm",
                        monthly_cost=monthly_cost,
                        usage_estimate=usage_estimate,
                        pricing_data=pricing_data,
                        notes=[f"Scaled by user growth factor: {scaling_multiplier}"]
                    )
                    state.cost_breakdowns.append(cost_breakdown)

    async def _calculate_infrastructure_costs(self, state: CostEstimationState) -> None:
        """Calculate infrastructure costs based on requirements."""
        # Base infrastructure for application hosting
        infra_pricing = next(
            (pricing for pricing in state.pricing_data if "compute" in pricing.service),
            None
        )

        if infra_pricing:
            # Estimate required compute hours based on availability and scaling
            availability_req = state.specification.infrastructure.availability_requirement
            availability_multiplier = 1.0 if availability_req < 99.5 else 2.0

            # Base compute cost
            monthly_hours = 730  # Hours in a month
            monthly_cost = monthly_hours * infra_pricing.unit_cost * availability_multiplier

            # Scale based on user count and complexity
            user_scaling = min(state.specification.application.expected_users / 1000, 10)  # Cap at 10x
            monthly_cost *= (1 + user_scaling * 0.1)

            cost_breakdown = CostBreakdown(
                component="infrastructure",
                category="infrastructure",
                monthly_cost=monthly_cost,
                usage_estimate=UsageEstimate(
                    component="compute_hours",
                    usage_amount=monthly_hours * availability_multiplier,
                    usage_unit="hours"
                ),
                pricing_data=infra_pricing,
                notes=[f"Availability multiplier: {availability_multiplier}"]
            )
            state.cost_breakdowns.append(cost_breakdown)

    async def _calculate_storage_costs(self, state: CostEstimationState) -> None:
        """Calculate storage and data-related costs."""
        for vector_config in state.specification.data_requirements.vector_stores:
            vector_pricing = next(
                (pricing for pricing in state.pricing_data
                 if pricing.provider == vector_config.provider),
                None
            )

            if vector_pricing:
                storage_gb = vector_config.storage_gb or 10.0  # Default 10GB
                monthly_cost = storage_gb * vector_pricing.unit_cost

                cost_breakdown = CostBreakdown(
                    component=f"vector_storage_{vector_config.provider}",
                    category="storage",
                    monthly_cost=monthly_cost,
                    usage_estimate=UsageEstimate(
                        component="vector_storage",
                        usage_amount=storage_gb,
                        usage_unit="gb"
                    ),
                    pricing_data=vector_pricing
                )
                state.cost_breakdowns.append(cost_breakdown)

    def _apply_interdependency_adjustments(self, state: CostEstimationState) -> None:
        """Apply adjustments based on component interdependencies."""
        # Apply coordination overhead to LLM costs
        llm_breakdowns = [cb for cb in state.cost_breakdowns if cb.category == "llm"]
        for breakdown in llm_breakdowns:
            overhead_cost = breakdown.monthly_cost * Decimal(str(state.coordination_overhead))
            breakdown.monthly_cost += overhead_cost
            breakdown.notes.append(f"Added coordination overhead: ${overhead_cost:.2f}")

    def _calculate_total_costs(self, state: CostEstimationState) -> None:
        """Calculate total monthly costs."""
        state.total_monthly_cost = sum(
            breakdown.monthly_cost for breakdown in state.cost_breakdowns
        )


class OptimizationAdvisorAgent(BaseAgent):
    """
    Identifies cost reduction opportunities and suggests alternatives.

    This agent analyzes the current cost structure and provides intelligent
    recommendations for reducing costs while maintaining functionality.
    """

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Generate optimization suggestions and alternative architectures."""
        state.log_agent_execution("OptimizationAdvisorAgent", "starting_optimization_analysis")

        if not state.cost_breakdowns:
            state.add_error("No cost breakdowns available for optimization", "OptimizationAdvisorAgent")
            return state

        try:
            # Analyze current cost structure
            await self._analyze_cost_structure(state)

            # Generate optimization suggestions
            await self._generate_optimization_suggestions(state)

            # Suggest alternative architectures
            await self._suggest_alternative_architectures(state)

            state.log_agent_execution("OptimizationAdvisorAgent", "optimization_complete", {
                "suggestions": len(state.optimization_suggestions),
                "alternatives": len(state.alternative_architectures)
            })

        except Exception as e:
            state.add_error(f"Error during optimization analysis: {str(e)}", "OptimizationAdvisorAgent")

        return state

    async def _analyze_cost_structure(self, state: CostEstimationState) -> None:
        """Analyze current cost structure to identify optimization opportunities."""
        cost_by_category = state.get_cost_by_category()
        total_cost = state.total_monthly_cost

        if not total_cost or total_cost == 0:
            return

        # Identify highest cost categories
        sorted_categories = sorted(
            cost_by_category.items(),
            key=lambda x: x[1],
            reverse=True
        )

        state.calculation_notes.append(
            f"Cost analysis: {', '.join([f'{cat}: ${cost:.2f}' for cat, cost in sorted_categories])}"
        )

    async def _generate_optimization_suggestions(self, state: CostEstimationState) -> None:
        """Generate specific cost optimization suggestions."""
        cost_by_category = state.get_cost_by_category()

        # LLM cost optimizations
        if "llm" in cost_by_category and cost_by_category["llm"] > Decimal("500"):
            suggestion = OptimizationSuggestion(
                title="Consider Model Optimization",
                description="High LLM costs detected. Consider using smaller models for simpler tasks or implementing caching.",
                category="llm",
                potential_savings=cost_by_category["llm"] * Decimal("0.3"),
                effort_level="medium",
                implementation_time="2-4 weeks",
                trade_offs=["Potential slight reduction in response quality", "Additional complexity in model routing"],
                confidence=0.8
            )
            state.optimization_suggestions.append(suggestion)

        # Infrastructure optimizations
        if "infrastructure" in cost_by_category and cost_by_category["infrastructure"] > Decimal("200"):
            suggestion = OptimizationSuggestion(
                title="Infrastructure Right-Sizing",
                description="Optimize compute resources based on actual usage patterns and implement auto-scaling.",
                category="infrastructure",
                potential_savings=cost_by_category["infrastructure"] * Decimal("0.25"),
                effort_level="low",
                implementation_time="1-2 weeks",
                trade_offs=["Initial setup time for monitoring", "Need for usage pattern analysis"],
                confidence=0.9
            )
            state.optimization_suggestions.append(suggestion)

    async def _suggest_alternative_architectures(self, state: CostEstimationState) -> None:
        """Suggest alternative architectural approaches."""
        # Self-hosted vs managed service analysis
        managed_costs = sum(
            breakdown.monthly_cost for breakdown in state.cost_breakdowns
            if "managed" in breakdown.component or breakdown.category in ["llm", "storage"]
        )

        if managed_costs > Decimal("1000"):
            alternative = {
                "name": "Hybrid Self-Hosted Architecture",
                "description": "Consider self-hosting some components to reduce recurring costs",
                "estimated_cost_reduction": managed_costs * Decimal("0.4"),
                "implementation_complexity": "high",
                "trade_offs": [
                    "Higher upfront infrastructure costs",
                    "Increased operational complexity",
                    "Need for specialized expertise"
                ],
                "recommended_for": "High-volume, stable workloads"
            }
            state.alternative_architectures.append(alternative)


class ReportGeneratorAgent(BaseAgent):
    """
    Creates comprehensive cost reports with executive summaries.

    This agent synthesizes all the analysis into clear, actionable reports
    suitable for both technical and business stakeholders.
    """

    async def invoke(
        self,
        state: CostEstimationState,
        config: Optional[RunnableConfig] = None
    ) -> CostEstimationState:
        """Generate comprehensive cost estimation report."""
        state.log_agent_execution("ReportGeneratorAgent", "starting_report_generation")

        try:
            # Generate executive summary
            await self._generate_executive_summary(state)

            # Generate detailed report
            await self._generate_detailed_report(state)

            # Generate recommendations
            self._generate_recommendations(state)

            state.log_agent_execution("ReportGeneratorAgent", "report_generation_complete")

        except Exception as e:
            state.add_error(f"Error during report generation: {str(e)}", "ReportGeneratorAgent")

        return state

    async def _generate_executive_summary(self, state: CostEstimationState) -> None:
        """Generate executive summary using LLM."""
        if not state.total_monthly_cost:
            return

        context = {
            "total_cost": float(state.total_monthly_cost),
            "cost_by_category": {k: float(v) for k, v in state.get_cost_by_category().items()},
            "confidence_score": state.get_confidence_score(),
            "optimization_savings": float(state.get_total_potential_savings()),
            "application_name": state.specification.application.name
        }

        system_prompt = """
        You are an expert financial analyst specializing in AI application cost analysis.
        Create a concise executive summary of the cost estimation results that business
        stakeholders can quickly understand and act upon.

        Focus on:
        1. Key cost drivers and total investment required
        2. Confidence level and risk factors
        3. Top optimization opportunities
        4. Strategic recommendations

        Keep it professional, clear, and actionable.
        """

        human_prompt = f"""
        Cost Estimation Results:
        {context}

        Please create an executive summary that highlights the key financial insights
        and strategic recommendations for this AI application deployment.
        """

        try:
            messages = [
                self._create_system_message(system_prompt),
                self._create_human_message(human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            state.executive_summary = response.content

        except Exception as e:
            state.add_warning(f"Could not generate executive summary: {str(e)}", "ReportGeneratorAgent")

    async def _generate_detailed_report(self, state: CostEstimationState) -> None:
        """Generate detailed technical report."""
        report_sections = []

        # Cost breakdown section
        report_sections.append("## Cost Breakdown\n")
        for category, cost in state.get_cost_by_category().items():
            report_sections.append(f"- **{category.title()}**: ${cost:.2f}")

        # Optimization suggestions section
        if state.optimization_suggestions:
            report_sections.append("\n## Optimization Opportunities\n")
            for suggestion in state.optimization_suggestions:
                report_sections.append(f"### {suggestion.title}")
                report_sections.append(f"{suggestion.description}")
                report_sections.append(f"**Potential Savings**: ${suggestion.potential_savings:.2f}")
                report_sections.append(f"**Effort Level**: {suggestion.effort_level}")
                report_sections.append("")

        state.detailed_report = "\n".join(report_sections)

    def _generate_recommendations(self, state: CostEstimationState) -> None:
        """Generate actionable recommendations."""
        recommendations = []

        # Cost-based recommendations
        if state.total_monthly_cost > Decimal("5000"):
            recommendations.append("Consider implementing cost monitoring and alerting")

        # Confidence-based recommendations
        if state.get_confidence_score() < 0.7:
            recommendations.append("Gather more detailed usage data to improve cost accuracy")

        # Optimization-based recommendations
        if state.optimization_suggestions:
            top_suggestion = max(state.optimization_suggestions, key=lambda x: x.potential_savings)
            recommendations.append(f"Priority optimization: {top_suggestion.title}")

        state.recommendations = recommendations