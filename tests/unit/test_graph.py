"""
Unit tests for the LangGraph orchestration and individual agents.

Tests the core agent functionality and workflow orchestration
without requiring external API calls.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from cost_estimator.graph.state import (
    CostEstimationState,
    UsageEstimate,
    PricingData,
    CostBreakdown,
    OptimizationSuggestion
)
from cost_estimator.graph.nodes import (
    InputParserAgent,
    UsagePatternAnalyzer,
    CostDiscoveryAgent,
    CalculationEngineAgent,
    OptimizationAdvisorAgent,
    ReportGeneratorAgent
)
from cost_estimator.graph.graph import CostEstimatorGraph
from cost_estimator.schemas import ApplicationSpecification


class TestCostEstimationState:
    """Test the central state object."""

    def test_state_initialization(self):
        """Test state initializes with correct defaults."""
        state = CostEstimationState()

        assert state.specification is None
        assert len(state.validation_errors) == 0
        assert len(state.usage_estimates) == 0
        assert len(state.cost_breakdowns) == 0
        assert state.total_monthly_cost is None

    def test_add_error_with_agent_context(self):
        """Test error tracking with agent context."""
        state = CostEstimationState()
        state.add_error("Test error", "TestAgent")

        assert len(state.errors) == 1
        assert "[TestAgent]" in state.errors[0]
        assert "Test error" in state.errors[0]

    def test_log_agent_execution(self):
        """Test agent execution logging."""
        state = CostEstimationState()
        state.log_agent_execution("TestAgent", "test_action", {"key": "value"})

        assert len(state.agent_execution_log) == 1
        log_entry = state.agent_execution_log[0]
        assert log_entry["agent"] == "TestAgent"
        assert log_entry["action"] == "test_action"
        assert log_entry["details"]["key"] == "value"

    def test_get_cost_by_category(self):
        """Test cost aggregation by category."""
        state = CostEstimationState()

        # Add some cost breakdowns
        usage_estimate = UsageEstimate(
            component="test_component",
            usage_amount=1000,
            usage_unit="tokens"
        )
        pricing_data = PricingData(
            service="test_service",
            provider="test_provider",
            region="us-east-1",
            unit_cost=Decimal("0.01"),
            unit_type="per_token"
        )

        breakdown1 = CostBreakdown(
            component="component1",
            category="llm",
            monthly_cost=Decimal("100.50"),
            usage_estimate=usage_estimate,
            pricing_data=pricing_data
        )
        breakdown2 = CostBreakdown(
            component="component2",
            category="llm",
            monthly_cost=Decimal("50.25"),
            usage_estimate=usage_estimate,
            pricing_data=pricing_data
        )
        breakdown3 = CostBreakdown(
            component="component3",
            category="infrastructure",
            monthly_cost=Decimal("200.00"),
            usage_estimate=usage_estimate,
            pricing_data=pricing_data
        )

        state.cost_breakdowns = [breakdown1, breakdown2, breakdown3]

        cost_by_category = state.get_cost_by_category()
        assert cost_by_category["llm"] == Decimal("150.75")
        assert cost_by_category["infrastructure"] == Decimal("200.00")

    def test_get_confidence_score(self):
        """Test confidence score calculation."""
        state = CostEstimationState()

        # Add cost breakdowns with different confidence levels
        usage_estimate1 = UsageEstimate(
            component="comp1",
            usage_amount=1000,
            usage_unit="tokens",
            confidence_level=0.9
        )
        pricing_data1 = PricingData(
            service="service1",
            provider="provider1",
            region="us-east-1",
            unit_cost=Decimal("100"),
            unit_type="per_unit",
            confidence_level=0.8
        )
        breakdown1 = CostBreakdown(
            component="comp1",
            category="llm",
            monthly_cost=Decimal("100"),
            usage_estimate=usage_estimate1,
            pricing_data=pricing_data1
        )

        usage_estimate2 = UsageEstimate(
            component="comp2",
            usage_amount=500,
            usage_unit="tokens",
            confidence_level=0.7
        )
        pricing_data2 = PricingData(
            service="service2",
            provider="provider2",
            region="us-east-1",
            unit_cost=Decimal("50"),
            unit_type="per_unit",
            confidence_level=0.9
        )
        breakdown2 = CostBreakdown(
            component="comp2",
            category="infrastructure",
            monthly_cost=Decimal("50"),
            usage_estimate=usage_estimate2,
            pricing_data=pricing_data2
        )

        state.cost_breakdowns = [breakdown1, breakdown2]

        confidence = state.get_confidence_score()
        # Should be weighted average: (100 * 0.9 * 0.8 + 50 * 0.7 * 0.9) / 150
        expected = (100 * 0.72 + 50 * 0.63) / 150
        assert abs(confidence - expected) < 0.01


class TestInputParserAgent:
    """Test the input parser agent."""

    @pytest.mark.asyncio
    async def test_parse_valid_specification(self):
        """Test parsing a valid specification."""
        agent = InputParserAgent()
        state = CostEstimationState()

        # Valid specification data
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test application"
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    }
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }
        state.raw_input = spec_data

        # Mock LLM for enrichment
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(content="Enrichment suggestions"))
            result_state = await agent.invoke(state)

        assert result_state.specification is not None
        assert result_state.specification.application.name == "Test App"
        assert len(result_state.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_parse_invalid_specification(self):
        """Test parsing an invalid specification."""
        agent = InputParserAgent()
        state = CostEstimationState()

        # Invalid specification data
        spec_data = {
            "application": {
                "name": "Test App"
                # Missing description
            },
            "agents": [],  # Empty agents
            "infrastructure": {
                "deployment_type": "invalid",
                "cloud_provider": "aws"
            }
        }
        state.raw_input = spec_data

        result_state = await agent.invoke(state)

        assert len(result_state.validation_errors) > 0
        assert result_state.specification is None


class TestUsagePatternAnalyzer:
    """Test the usage pattern analyzer agent."""

    @pytest.mark.asyncio
    async def test_analyze_usage_patterns(self):
        """Test usage pattern analysis."""
        agent = UsagePatternAnalyzer()
        state = CostEstimationState()

        # Set up a specification
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test application",
                "expected_users": 1000,
                "usage_patterns": {
                    "sessions_per_user_month": 10,
                    "avg_session_duration_minutes": 15
                }
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    },
                    "complexity": "medium",
                    "interaction_frequency": "on_demand"
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }
        state.specification = ApplicationSpecification(**spec_data)

        # Mock LLM for analysis
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(content="Usage analysis"))
            result_state = await agent.invoke(state)

        assert len(result_state.usage_estimates) > 0
        assert result_state.coordination_overhead >= 0.0
        assert len(result_state.scaling_factors) > 0

    def test_calculate_base_token_usage(self):
        """Test base token usage calculation."""
        agent = UsagePatternAnalyzer()
        state = CostEstimationState()

        # Set up specification
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test",
                "expected_users": 100,
                "usage_patterns": {
                    "sessions_per_user_month": 10,
                    "avg_session_duration_minutes": 15
                }
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    },
                    "complexity": "medium",
                    "interaction_frequency": "on_demand",
                    "coordination_overhead": 0.1
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }
        state.specification = ApplicationSpecification(**spec_data)

        agent_config = state.specification.agents[0]
        tokens = agent._calculate_base_token_usage(state, agent_config)

        # Should be: 100 users * 10 sessions * 15 minutes * 100 tokens/min * complexity * frequency
        # = 100 * 10 * 15 * 100 * 1.0 * 0.3 = 450,000 tokens
        assert tokens > 0
        assert isinstance(tokens, float)


class TestCostDiscoveryAgent:
    """Test the cost discovery agent."""

    @pytest.mark.asyncio
    async def test_discover_pricing_data(self):
        """Test pricing data discovery."""
        agent = CostDiscoveryAgent()
        state = CostEstimationState()

        # Set up specification
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test"
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    }
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            },
            "data_requirements": {
                "vector_stores": [
                    {
                        "provider": "pinecone",
                        "deployment_mode": "managed"
                    }
                ]
            }
        }
        state.specification = ApplicationSpecification(**spec_data)

        result_state = await agent.invoke(state)

        assert len(result_state.pricing_data) > 0
        assert result_state.pricing_confidence > 0

    def test_fallback_pricing(self):
        """Test fallback pricing when live pricing fails."""
        agent = CostDiscoveryAgent()

        fallback_pricing = agent._get_fallback_llm_pricing("unknown_provider", "unknown_model")

        assert isinstance(fallback_pricing, PricingData)
        assert fallback_pricing.provider == "unknown_provider"
        assert fallback_pricing.confidence_level < 1.0
        assert fallback_pricing.source == "cached"


class TestCalculationEngineAgent:
    """Test the calculation engine agent."""

    @pytest.mark.asyncio
    async def test_calculate_costs(self):
        """Test cost calculation."""
        agent = CalculationEngineAgent()
        state = CostEstimationState()

        # Set up state with usage estimates and pricing data
        usage_estimate = UsageEstimate(
            component="TestAgent_tokens",
            usage_amount=100000,
            usage_unit="tokens",
            confidence_level=0.8
        )
        pricing_data = PricingData(
            service="openai_gpt-3.5-turbo",
            provider="openai",
            region="global",
            unit_cost=Decimal("0.001"),
            unit_type="per_1k_tokens",
            confidence_level=0.9
        )

        state.usage_estimates = [usage_estimate]
        state.pricing_data = [pricing_data]
        state.scaling_factors = {"user_growth": 1.1}

        # Set up specification
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test"
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    }
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }
        state.specification = ApplicationSpecification(**spec_data)

        result_state = await agent.invoke(state)

        assert len(result_state.cost_breakdowns) > 0
        assert result_state.total_monthly_cost is not None
        assert result_state.total_monthly_cost > 0


class TestCostEstimatorGraph:
    """Test the main graph orchestration."""

    @pytest.mark.asyncio
    async def test_estimate_costs_basic(self):
        """Test basic cost estimation workflow."""
        estimator = CostEstimatorGraph()

        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test application"
            },
            "agents": [
                {
                    "name": "TestAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    }
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }

        # Mock the agents to avoid external API calls
        with patch.multiple(
            estimator._agents["input_parser"],
            invoke=AsyncMock(return_value=CostEstimationState())
        ):
            result = await estimator.estimate_costs(spec_data)

        assert isinstance(result, CostEstimationState)
        assert result.estimation_id is not None

    def test_validate_specification(self):
        """Test specification validation."""
        estimator = CostEstimatorGraph()

        valid_spec = {
            "application": {
                "name": "Valid App",
                "description": "Valid application"
            },
            "agents": [
                {
                    "name": "ValidAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-3.5-turbo",
                        "provider": "openai"
                    }
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }

        result = estimator.validate_specification(valid_spec)
        assert result["valid"] is True
        assert "specification" in result

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        estimator = CostEstimatorGraph()
        providers = estimator.get_supported_providers()

        assert "llm_providers" in providers
        assert "cloud_providers" in providers
        assert "vector_db_providers" in providers
        assert len(providers["llm_providers"]) > 0


# Fixtures for testing
@pytest.fixture
def sample_state():
    """Sample cost estimation state for testing."""
    state = CostEstimationState()
    state.estimation_id = "test-123"
    return state


@pytest.fixture
def sample_usage_estimate():
    """Sample usage estimate for testing."""
    return UsageEstimate(
        component="test_component",
        usage_amount=1000,
        usage_unit="tokens",
        confidence_level=0.8
    )


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return PricingData(
        service="test_service",
        provider="test_provider",
        region="us-east-1",
        unit_cost=Decimal("0.01"),
        unit_type="per_token",
        confidence_level=0.9
    )