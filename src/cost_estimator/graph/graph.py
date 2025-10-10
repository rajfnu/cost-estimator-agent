"""
Main LangGraph orchestration for cost estimation workflow.

This module defines the graph structure and execution flow for the
intelligent cost estimation system, coordinating all specialized agents.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import CostEstimationState
from .nodes import (
    InputParserAgent,
    UsagePatternAnalyzer,
    CostDiscoveryAgent,
    CalculationEngineAgent,
    OptimizationAdvisorAgent,
    ReportGeneratorAgent,
)
from ..cache import get_cache_manager
from ..config import get_config

logger = logging.getLogger(__name__)


class CostEstimatorGraph:
    """
    Main orchestrator for the cost estimation workflow.

    This class builds and manages the LangGraph that coordinates all
    cost estimation agents, handling both sequential dependencies
    and parallel processing where possible.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the cost estimator graph."""
        self.config = config or {}
        self._graph = None
        self._agents = {}
        self._setup_agents()
        self._build_graph()

    def _setup_agents(self) -> None:
        """Initialize all agents with configuration."""
        # Common LLM configuration
        llm_config = self.config.get("llm", {})

        # Initialize agents
        self._agents = {
            "input_parser": InputParserAgent(),
            "usage_analyzer": UsagePatternAnalyzer(),
            "cost_discovery": CostDiscoveryAgent(),
            "calculation_engine": CalculationEngineAgent(),
            "optimization_advisor": OptimizationAdvisorAgent(),
            "report_generator": ReportGeneratorAgent(),
        }

    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        # Create the state graph
        graph = StateGraph(CostEstimationState)

        # Add nodes
        graph.add_node("parse_input", self._parse_input_node)
        graph.add_node("analyze_usage", self._analyze_usage_node)
        graph.add_node("discover_pricing", self._discover_pricing_node)
        graph.add_node("calculate_costs", self._calculate_costs_node)
        graph.add_node("optimize_costs", self._optimize_costs_node)
        graph.add_node("generate_report", self._generate_report_node)

        # Define the workflow edges
        graph.add_edge(START, "parse_input")
        graph.add_edge("parse_input", "analyze_usage")

        # Parallel execution for usage analysis and price discovery
        graph.add_edge("analyze_usage", "discover_pricing")
        graph.add_edge("discover_pricing", "calculate_costs")

        # Sequential execution for calculation and optimization
        graph.add_edge("calculate_costs", "optimize_costs")
        graph.add_edge("optimize_costs", "generate_report")
        graph.add_edge("generate_report", END)

        # Add conditional edges for error handling
        graph.add_conditional_edges(
            "parse_input",
            self._should_continue_after_parsing,
            {
                "continue": "analyze_usage",
                "error": END
            }
        )

        # Compile the graph with memory for state persistence
        memory = MemorySaver()
        self._graph = graph.compile(checkpointer=memory)

    async def _parse_input_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for input parsing agent."""
        return await self._agents["input_parser"].invoke(state)

    async def _analyze_usage_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for usage pattern analyzer."""
        return await self._agents["usage_analyzer"].invoke(state)

    async def _discover_pricing_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for cost discovery agent."""
        return await self._agents["cost_discovery"].invoke(state)

    async def _calculate_costs_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for calculation engine."""
        return await self._agents["calculation_engine"].invoke(state)

    async def _optimize_costs_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for optimization advisor."""
        return await self._agents["optimization_advisor"].invoke(state)

    async def _generate_report_node(self, state: CostEstimationState) -> CostEstimationState:
        """Node wrapper for report generator."""
        return await self._agents["report_generator"].invoke(state)

    def _should_continue_after_parsing(self, state: CostEstimationState) -> str:
        """Conditional logic to determine if workflow should continue after parsing."""
        if state.has_errors():
            return "error"
        return "continue"

    def _dict_to_state(self, state_dict: Dict[str, Any]) -> CostEstimationState:
        """Convert dictionary back to CostEstimationState object."""
        from .state import CostEstimationState, CostBreakdown, UsageEstimate, PricingData, OptimizationSuggestion, ScenarioAnalysis
        from decimal import Decimal

        # Create a new state object
        state = CostEstimationState()

        # Copy simple fields
        for field_name, value in state_dict.items():
            if hasattr(state, field_name):
                setattr(state, field_name, value)

        return state

    async def estimate_costs(
        self,
        specification: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> CostEstimationState:
        """
        Main entry point for cost estimation with intelligent caching.

        Args:
            specification: Application specification dictionary
            options: Additional estimation options (force_refresh, etc.)

        Returns:
            Complete cost estimation state with results
        """
        options = options or {}
        force_refresh = options.get("force_refresh", False)

        # Get cache manager and config
        config = get_config()
        cache_manager = get_cache_manager()

        # Check cache first (unless force_refresh is True)
        if config.cache.cache_enabled and not force_refresh:
            cached_result = cache_manager.get_estimation(specification)
            if cached_result is not None:
                logger.info("✅ Using cached estimation result - no LLM/API calls needed")
                # Add cache hit indicator
                cached_result.calculation_notes.append("Result retrieved from cache")
                return cached_result

        # Initialize state
        initial_state = CostEstimationState(
            estimation_id=str(uuid.uuid4()),
            estimation_timestamp=datetime.now().isoformat(),
            raw_input=specification
        )

        # Record start time
        start_time = datetime.now()

        try:
            logger.info(f"Starting cost estimation for: {specification.get('application', {}).get('name', 'Unknown')}")

            # Execute the graph
            config_dict = {"configurable": {"thread_id": initial_state.estimation_id}}
            final_state = await self._graph.ainvoke(initial_state, config=config_dict)

            # LangGraph converts dataclass to dict, so we need to convert it back
            if isinstance(final_state, dict):
                logger.info("Converting dict result back to CostEstimationState")
                final_state = self._dict_to_state(final_state)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            final_state.processing_time_seconds = processing_time

            logger.info(f"Cost estimation completed in {processing_time:.2f} seconds")

            # Log summary
            if final_state.total_monthly_cost:
                logger.info(f"Estimated monthly cost: ${final_state.total_monthly_cost:.2f}")
                logger.info(f"Confidence score: {final_state.get_confidence_score():.2f}")

            if final_state.has_errors():
                logger.warning(f"Estimation completed with {len(final_state.errors)} errors")

            # Cache the result if caching is enabled and estimation was successful
            if config.cache.cache_enabled and not final_state.has_errors():
                cache_manager.set_estimation(
                    specification,
                    final_state,
                    ttl=config.cache.estimation_cache_ttl
                )
                logger.info("💾 Cached estimation result for future use")

            return final_state

        except Exception as e:
            logger.error(f"Cost estimation failed: {str(e)}")
            initial_state.add_error(f"Graph execution failed: {str(e)}", "CostEstimatorGraph")
            return initial_state

    async def estimate_costs_with_scenarios(
        self,
        specification: Dict[str, Any],
        scenarios: Optional[List[str]] = None
    ) -> Dict[str, CostEstimationState]:
        """
        Estimate costs for multiple scenarios.

        Args:
            specification: Base application specification
            scenarios: List of scenario names to analyze

        Returns:
            Dictionary mapping scenario names to estimation results
        """
        scenarios = scenarios or ["conservative", "expected", "optimistic"]
        results = {}

        # Base estimation
        base_result = await self.estimate_costs(specification)
        results["base"] = base_result

        # Generate scenario variations
        for scenario in scenarios:
            if scenario == "base":
                continue

            # Modify specification for scenario
            scenario_spec = self._create_scenario_specification(specification, scenario)
            scenario_result = await self.estimate_costs(scenario_spec)
            results[scenario] = scenario_result

        return results

    def _create_scenario_specification(
        self,
        base_spec: Dict[str, Any],
        scenario: str
    ) -> Dict[str, Any]:
        """Create a modified specification for scenario analysis."""
        import copy
        scenario_spec = copy.deepcopy(base_spec)

        # Modify based on scenario type
        if scenario == "conservative":
            # Increase usage by 50% and add redundancy
            if "application" in scenario_spec and "usage_patterns" in scenario_spec["application"]:
                usage = scenario_spec["application"]["usage_patterns"]
                usage["sessions_per_user_month"] = int(usage.get("sessions_per_user_month", 10) * 1.5)
                usage["peak_concurrency_ratio"] = min(usage.get("peak_concurrency_ratio", 0.1) * 1.5, 1.0)

        elif scenario == "optimistic":
            # Reduce usage by 25% and assume efficiency gains
            if "application" in scenario_spec and "usage_patterns" in scenario_spec["application"]:
                usage = scenario_spec["application"]["usage_patterns"]
                usage["sessions_per_user_month"] = int(usage.get("sessions_per_user_month", 10) * 0.75)
                usage["peak_concurrency_ratio"] = usage.get("peak_concurrency_ratio", 0.1) * 0.8

        return scenario_spec

    async def get_estimation_history(self, estimation_id: str) -> Optional[CostEstimationState]:
        """Retrieve a previous estimation by ID."""
        # This would integrate with the checkpointer to retrieve historical states
        # For now, return None as this requires database integration
        return None

    def get_supported_providers(self) -> Dict[str, List[str]]:
        """Get list of supported cloud and AI service providers."""
        return {
            "llm_providers": ["openai", "anthropic", "azure_openai", "aws_bedrock", "gcp_vertex"],
            "cloud_providers": ["aws", "azure", "gcp"],
            "vector_db_providers": ["pinecone", "weaviate", "qdrant", "chroma", "milvus"],
        }

    def validate_specification(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate specification without running full estimation.

        Returns:
            Dictionary with validation results
        """
        from ..schemas import ApplicationSpecification

        try:
            # Parse specification
            parsed_spec = ApplicationSpecification(**specification)

            return {
                "valid": True,
                "specification": parsed_spec.dict(),
                "warnings": [],
                "suggestions": []
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "suggestions": []
            }

    async def estimate_costs_streaming(
        self,
        specification: Dict[str, Any],
        callback: Optional[callable] = None
    ) -> CostEstimationState:
        """
        Stream estimation progress with callbacks.

        Args:
            specification: Application specification
            callback: Function called with progress updates

        Returns:
            Final estimation state
        """
        if not callback:
            return await self.estimate_costs(specification)

        # Initialize state
        initial_state = CostEstimationState(
            estimation_id=str(uuid.uuid4()),
            estimation_timestamp=datetime.now().isoformat(),
            raw_input=specification
        )

        # Stream progress through the graph
        config = {"configurable": {"thread_id": initial_state.estimation_id}}

        try:
            # Execute graph with streaming
            async for state in self._graph.astream(initial_state, config=config):
                # Call progress callback
                if callback:
                    await callback(state)

            # Get final state
            final_state = await self._graph.ainvoke(initial_state, config=config)
            return final_state

        except Exception as e:
            logger.error(f"Streaming estimation failed: {str(e)}")
            initial_state.add_error(f"Streaming execution failed: {str(e)}", "CostEstimatorGraph")
            return initial_state


# Convenience function for quick estimations
async def estimate_application_costs(
    specification: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> CostEstimationState:
    """
    Convenience function for quick cost estimation.

    Args:
        specification: Application specification dictionary
        config: Optional configuration for the estimation

    Returns:
        Cost estimation results
    """
    estimator = CostEstimatorGraph(config)
    return await estimator.estimate_costs(specification)