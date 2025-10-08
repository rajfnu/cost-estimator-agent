"""
Unit tests for Pydantic schemas and validation.

Tests the core data structures and validation logic for
application specifications and cost estimation requests.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from cost_estimator.schemas import (
    ApplicationSpecification,
    AgentConfiguration,
    LLMConfiguration,
    UsagePatterns,
    ApplicationMetadata,
    CostEstimationRequest,
    validate_specification,
)


class TestApplicationSpecification:
    """Test the main application specification schema."""

    def test_minimal_valid_specification(self):
        """Test that a minimal specification is valid."""
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

        spec = ApplicationSpecification(**spec_data)
        assert spec.application.name == "Test App"
        assert len(spec.agents) == 1
        assert spec.agents[0].name == "TestAgent"

    def test_complex_specification(self):
        """Test a complex specification with all fields."""
        spec_data = {
            "application": {
                "name": "Complex App",
                "description": "Complex test application",
                "complexity": "high",
                "expected_users": 5000,
                "usage_patterns": {
                    "sessions_per_user_month": 20,
                    "avg_session_duration_minutes": 15
                },
                "industry": "fintech",
                "compliance_requirements": ["SOC2", "GDPR"]
            },
            "agents": [
                {
                    "name": "MainAgent",
                    "role": "primary",
                    "llm_config": {
                        "name": "gpt-4-turbo",
                        "provider": "openai",
                        "deployment_mode": "api",
                        "expected_tokens_per_request": 1000
                    },
                    "tools": [
                        {
                            "name": "test_tool",
                            "type": "api",
                            "usage_frequency": "frequent"
                        }
                    ],
                    "complexity": "high"
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws",
                "region": "us-east-1",
                "availability_requirement": 99.9
            },
            "data_requirements": {
                "vector_stores": [
                    {
                        "provider": "pinecone",
                        "deployment_mode": "managed",
                        "estimated_vectors": 100000
                    }
                ]
            }
        }

        spec = ApplicationSpecification(**spec_data)
        assert spec.application.complexity == "high"
        assert spec.application.expected_users == 5000
        assert len(spec.agents) == 1
        assert len(spec.data_requirements.vector_stores) == 1

    def test_invalid_specification_missing_required(self):
        """Test that missing required fields raise validation errors."""
        spec_data = {
            "application": {
                "name": "Test App"
                # Missing description
            },
            "agents": [],  # Empty agents list should fail
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }

        with pytest.raises(ValidationError) as exc_info:
            ApplicationSpecification(**spec_data)

        errors = exc_info.value.errors()
        # Should have errors for missing description and empty agents
        assert len(errors) >= 2

    def test_coordination_overhead_validation(self):
        """Test that coordination overhead is properly validated."""
        spec_data = {
            "application": {
                "name": "Test App",
                "description": "Test"
            },
            "agents": [
                {
                    "name": "HighComplexityAgent",
                    "role": "test",
                    "llm_config": {
                        "name": "gpt-4",
                        "provider": "openai"
                    },
                    "complexity": "high",
                    "coordination_overhead": 0.05  # Too low for high complexity
                }
            ],
            "infrastructure": {
                "deployment_type": "cloud",
                "cloud_provider": "aws"
            }
        }

        spec = ApplicationSpecification(**spec_data)
        # Should be adjusted to minimum for high complexity
        assert spec.agents[0].coordination_overhead >= 0.15


class TestUsagePatterns:
    """Test usage pattern validation and defaults."""

    def test_default_usage_patterns(self):
        """Test that default usage patterns are reasonable."""
        patterns = UsagePatterns()

        assert patterns.sessions_per_user_month == 10
        assert patterns.avg_session_duration_minutes == 15.0
        assert patterns.peak_concurrency_ratio == 0.1
        assert patterns.retention_rate == 0.8

    def test_usage_pattern_validation(self):
        """Test usage pattern field validation."""
        # Test valid patterns
        patterns = UsagePatterns(
            sessions_per_user_month=20,
            avg_session_duration_minutes=30.0,
            peak_concurrency_ratio=0.2
        )
        assert patterns.sessions_per_user_month == 20

        # Test invalid patterns
        with pytest.raises(ValidationError):
            UsagePatterns(sessions_per_user_month=0)  # Should be >= 1

        with pytest.raises(ValidationError):
            UsagePatterns(peak_concurrency_ratio=1.5)  # Should be <= 1.0


class TestLLMConfiguration:
    """Test LLM configuration validation."""

    def test_basic_llm_config(self):
        """Test basic LLM configuration."""
        config = LLMConfiguration(
            name="gpt-3.5-turbo",
            provider="openai"
        )

        assert config.name == "gpt-3.5-turbo"
        assert config.provider == "openai"
        assert config.deployment_mode == "api"  # Default

    def test_self_hosted_llm_config(self):
        """Test self-hosted LLM configuration."""
        config = LLMConfiguration(
            name="llama-2-70b",
            provider="self_hosted",
            deployment_mode="self_hosted",
            gpu_requirements={
                "gpu_type": "A100",
                "gpu_count": 4,
                "memory_gb": 320
            }
        )

        assert config.deployment_mode == "self_hosted"
        assert config.gpu_requirements["gpu_type"] == "A100"


class TestCostEstimationRequest:
    """Test cost estimation request validation."""

    def test_basic_estimation_request(self):
        """Test basic estimation request."""
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

        spec = ApplicationSpecification(**spec_data)
        request = CostEstimationRequest(specification=spec)

        assert request.specification.application.name == "Test App"
        assert request.scenario_analysis is True  # Default
        assert request.optimization_suggestions is True  # Default

    def test_estimation_request_with_options(self):
        """Test estimation request with custom options."""
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

        spec = ApplicationSpecification(**spec_data)
        request = CostEstimationRequest(
            specification=spec,
            estimation_options={"region_override": "eu-west-1"},
            scenario_analysis=False,
            optimization_suggestions=False
        )

        assert request.estimation_options["region_override"] == "eu-west-1"
        assert request.scenario_analysis is False
        assert request.optimization_suggestions is False


class TestValidationFunction:
    """Test the standalone validation function."""

    def test_validate_specification_success(self):
        """Test successful specification validation."""
        spec_dict = {
            "application": {
                "name": "Valid App",
                "description": "Valid test application"
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

        spec = validate_specification(spec_dict)
        assert isinstance(spec, ApplicationSpecification)
        assert spec.application.name == "Valid App"

    def test_validate_specification_failure(self):
        """Test specification validation failure."""
        spec_dict = {
            "application": {
                "name": "Invalid App"
                # Missing description
            },
            "agents": [],  # Empty agents
            "infrastructure": {
                "deployment_type": "invalid_type",  # Invalid enum
                "cloud_provider": "aws"
            }
        }

        with pytest.raises(ValidationError):
            validate_specification(spec_dict)


# Fixtures for common test data
@pytest.fixture
def minimal_spec_data():
    """Minimal valid specification data."""
    return {
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


@pytest.fixture
def complex_spec_data():
    """Complex specification data for testing."""
    return {
        "application": {
            "name": "Complex App",
            "description": "Complex test application",
            "complexity": "high",
            "expected_users": 5000,
            "usage_patterns": {
                "sessions_per_user_month": 25,
                "avg_session_duration_minutes": 20,
                "peak_concurrency_ratio": 0.15
            }
        },
        "agents": [
            {
                "name": "PrimaryAgent",
                "role": "primary",
                "llm_config": {
                    "name": "gpt-4-turbo",
                    "provider": "openai",
                    "deployment_mode": "api"
                },
                "complexity": "high",
                "tools": [
                    {
                        "name": "tool1",
                        "type": "api",
                        "usage_frequency": "frequent"
                    }
                ]
            },
            {
                "name": "SecondaryAgent",
                "role": "secondary",
                "llm_config": {
                    "name": "claude-3-sonnet",
                    "provider": "anthropic"
                },
                "complexity": "medium"
            }
        ],
        "infrastructure": {
            "deployment_type": "cloud",
            "cloud_provider": "aws",
            "region": "us-east-1",
            "availability_requirement": 99.9
        },
        "data_requirements": {
            "vector_stores": [
                {
                    "provider": "pinecone",
                    "deployment_mode": "managed",
                    "estimated_vectors": 500000,
                    "vector_dimensions": 1536
                }
            ],
            "document_processing_monthly": 10000
        }
    }