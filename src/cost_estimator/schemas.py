"""
Pydantic schemas for multi-agent application cost estimation.

This module defines the data structures for representing multi-agent AI applications
and their cost estimation requirements. The schemas are designed to be intelligent
and self-validating, enabling the agent system to reason about costs effectively.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from decimal import Decimal

from pydantic import BaseModel, Field, validator, root_validator


class ComplexityLevel(str, Enum):
    """Application or component complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ON_PREMISE = "on_premise"
    HYBRID = "hybrid"


class DeploymentType(str, Enum):
    """Deployment strategies."""
    CLOUD = "cloud"
    ON_PREMISE = "on_premise"
    HYBRID = "hybrid"
    EDGE = "edge"


class ScalingStrategy(str, Enum):
    """Scaling approaches."""
    MANUAL = "manual"
    AUTO = "auto"
    PREDICTIVE = "predictive"
    SERVERLESS = "serverless"


class LLMProvider(str, Enum):
    """LLM service providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    GCP_VERTEX = "gcp_vertex"
    HUGGING_FACE = "hugging_face"
    SELF_HOSTED = "self_hosted"
    LOCAL = "local"


class VectorDBProvider(str, Enum):
    """Vector database providers."""
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"
    MONGODB_ATLAS = "mongodb_atlas"
    SELF_HOSTED = "self_hosted"


class UsagePatterns(BaseModel):
    """User interaction and usage patterns."""
    sessions_per_user_month: int = Field(
        default=10,
        ge=1,
        description="Average sessions per user per month"
    )
    avg_session_duration_minutes: float = Field(
        default=15.0,
        ge=0.1,
        description="Average session duration in minutes"
    )
    peak_concurrency_ratio: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Peak concurrent users as ratio of total users"
    )
    seasonal_variance: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Seasonal usage variance multiplier"
    )
    growth_rate_monthly: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Expected monthly growth rate"
    )
    retention_rate: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="User retention rate"
    )


class ApplicationMetadata(BaseModel):
    """Core application information and characteristics."""
    name: str = Field(description="Application name")
    description: str = Field(description="Detailed application description")
    complexity: ComplexityLevel = Field(
        default=ComplexityLevel.MEDIUM,
        description="Overall application complexity"
    )
    expected_users: int = Field(
        default=1000,
        ge=1,
        description="Expected number of active users"
    )
    usage_patterns: UsagePatterns = Field(
        default_factory=UsagePatterns,
        description="User interaction patterns"
    )
    industry: Optional[str] = Field(
        default=None,
        description="Industry vertical (affects compliance and scaling requirements)"
    )
    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Regulatory compliance requirements (GDPR, HIPAA, SOC2, etc.)"
    )


class LLMConfiguration(BaseModel):
    """LLM model configuration with intelligent cost modeling."""
    name: str = Field(description="Model name (e.g., 'gpt-4-turbo', 'claude-3-opus')")
    provider: LLMProvider = Field(description="LLM provider")
    model_size: Optional[str] = Field(
        default=None,
        description="Model size indicator for self-hosted models"
    )
    deployment_mode: Literal["api", "self_hosted", "hybrid"] = Field(
        default="api",
        description="How the model is deployed"
    )

    # Cost estimation parameters
    expected_tokens_per_request: Optional[int] = Field(
        default=None,
        description="Override default token estimation"
    )
    context_window_size: Optional[int] = Field(
        default=None,
        description="Model context window size"
    )

    # Self-hosted specific
    gpu_requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description="GPU requirements for self-hosted deployment"
    )
    serving_framework: Optional[str] = Field(
        default=None,
        description="Serving framework (vLLM, TGI, etc.)"
    )

    # Performance characteristics
    latency_requirements_ms: Optional[int] = Field(
        default=None,
        description="Required response latency in milliseconds"
    )
    throughput_requirements_rps: Optional[float] = Field(
        default=None,
        description="Required throughput in requests per second"
    )


class ToolConfiguration(BaseModel):
    """Configuration for tools used by agents."""
    name: str = Field(description="Tool name")
    type: str = Field(description="Tool type (api, local, integration)")
    provider: Optional[str] = Field(default=None, description="Tool provider")
    usage_frequency: Literal["rare", "occasional", "frequent", "continuous"] = Field(
        default="occasional",
        description="How frequently the tool is used"
    )
    cost_per_usage: Optional[Decimal] = Field(
        default=None,
        description="Cost per tool usage if known"
    )
    api_calls_per_session: Optional[int] = Field(
        default=None,
        description="Average API calls per session"
    )


class AgentConfiguration(BaseModel):
    """Individual agent configuration with role and capabilities."""
    name: str = Field(description="Agent name")
    role: str = Field(description="Agent role in the system")
    llm_config: LLMConfiguration = Field(description="LLM configuration for this agent")
    tools: List[ToolConfiguration] = Field(
        default_factory=list,
        description="Tools available to this agent"
    )
    complexity: ComplexityLevel = Field(
        default=ComplexityLevel.MEDIUM,
        description="Agent complexity level"
    )
    interaction_frequency: Literal["on_demand", "periodic", "continuous"] = Field(
        default="on_demand",
        description="How frequently the agent is activated"
    )
    coordination_overhead: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Additional overhead for multi-agent coordination"
    )

    # Advanced configuration
    prompt_engineering_complexity: ComplexityLevel = Field(
        default=ComplexityLevel.MEDIUM,
        description="Complexity of prompt engineering required"
    )
    memory_requirements: Optional[str] = Field(
        default=None,
        description="Memory/state management requirements"
    )

    @validator('coordination_overhead')
    def validate_coordination_overhead(cls, v, values):
        """Adjust coordination overhead based on complexity."""
        complexity = values.get('complexity', ComplexityLevel.MEDIUM)
        if complexity == ComplexityLevel.HIGH and v < 0.15:
            return 0.15
        elif complexity == ComplexityLevel.CRITICAL and v < 0.25:
            return 0.25
        return v


class VectorStoreConfiguration(BaseModel):
    """Vector database configuration."""
    provider: VectorDBProvider = Field(description="Vector database provider")
    deployment_mode: Literal["managed", "self_hosted"] = Field(
        default="managed",
        description="Deployment mode"
    )

    # Capacity planning
    estimated_vectors: int = Field(
        default=100000,
        ge=1,
        description="Estimated number of vectors"
    )
    vector_dimensions: int = Field(
        default=1536,
        ge=1,
        description="Vector dimensions"
    )
    storage_gb: Optional[float] = Field(
        default=None,
        description="Estimated storage requirements in GB"
    )

    # Performance requirements
    queries_per_second: float = Field(
        default=10.0,
        ge=0.1,
        description="Expected queries per second"
    )
    index_rebuild_frequency: Literal["never", "weekly", "daily", "real_time"] = Field(
        default="weekly",
        description="How often the index needs rebuilding"
    )

    # Self-hosted specific
    infrastructure_requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Infrastructure requirements for self-hosted deployment"
    )


class DataRequirements(BaseModel):
    """Data processing and storage requirements."""
    vector_stores: List[VectorStoreConfiguration] = Field(
        default_factory=list,
        description="Vector database configurations"
    )
    document_processing_monthly: int = Field(
        default=1000,
        ge=0,
        description="Documents processed per month"
    )
    data_ingestion_gb_monthly: float = Field(
        default=10.0,
        ge=0.0,
        description="Data ingestion volume in GB per month"
    )
    real_time_sync_required: bool = Field(
        default=False,
        description="Whether real-time data synchronization is required"
    )
    backup_retention_days: int = Field(
        default=30,
        ge=1,
        description="Backup retention period in days"
    )
    compliance_encryption: bool = Field(
        default=False,
        description="Whether compliance-grade encryption is required"
    )


class InfrastructureConfiguration(BaseModel):
    """Infrastructure deployment configuration."""
    deployment_type: DeploymentType = Field(description="Deployment strategy")
    cloud_provider: CloudProvider = Field(description="Primary cloud provider")
    region: str = Field(default="us-east-1", description="Deployment region")
    availability_zones: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Number of availability zones"
    )
    scaling_strategy: ScalingStrategy = Field(
        default=ScalingStrategy.AUTO,
        description="Scaling approach"
    )
    availability_requirement: float = Field(
        default=99.9,
        ge=90.0,
        le=99.99,
        description="Availability SLA percentage"
    )

    # Networking and security
    load_balancing_required: bool = Field(
        default=True,
        description="Whether load balancing is required"
    )
    cdn_required: bool = Field(
        default=False,
        description="Whether CDN is required"
    )
    vpn_required: bool = Field(
        default=False,
        description="Whether VPN access is required"
    )

    # Monitoring and observability
    monitoring_level: ComplexityLevel = Field(
        default=ComplexityLevel.MEDIUM,
        description="Required monitoring complexity"
    )
    logging_retention_days: int = Field(
        default=90,
        ge=1,
        description="Log retention period"
    )


class CostConstraints(BaseModel):
    """Budget constraints and optimization preferences."""
    monthly_budget_usd: Optional[Decimal] = Field(
        default=None,
        description="Maximum monthly budget in USD"
    )
    cost_optimization_priority: List[str] = Field(
        default_factory=lambda: ["llm_costs", "infrastructure", "storage"],
        description="Cost optimization priority order"
    )
    acceptable_performance_tradeoff: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Acceptable performance degradation for cost savings"
    )
    prefer_managed_services: bool = Field(
        default=True,
        description="Preference for managed vs self-hosted services"
    )


class ApplicationSpecification(BaseModel):
    """Complete multi-agent application specification."""
    application: ApplicationMetadata = Field(description="Application metadata")
    agents: List[AgentConfiguration] = Field(
        description="Agent configurations",
        min_items=1
    )
    infrastructure: InfrastructureConfiguration = Field(
        description="Infrastructure configuration"
    )
    data_requirements: DataRequirements = Field(
        default_factory=DataRequirements,
        description="Data and storage requirements"
    )
    cost_constraints: Optional[CostConstraints] = Field(
        default=None,
        description="Budget constraints and preferences"
    )

    # Validation and enrichment metadata
    specification_version: str = Field(
        default="1.0",
        description="Specification schema version"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Specification creation timestamp"
    )

    @root_validator
    def validate_application_consistency(cls, values):
        """Validate overall application consistency."""
        agents = values.get('agents', [])
        infrastructure = values.get('infrastructure')
        app_metadata = values.get('application')

        # Ensure complexity alignment
        if app_metadata and infrastructure:
            high_complexity_agents = [a for a in agents if a.complexity in [ComplexityLevel.HIGH, ComplexityLevel.CRITICAL]]
            if high_complexity_agents and infrastructure.availability_requirement < 99.5:
                infrastructure.availability_requirement = 99.5

        return values

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "application": {
                    "name": "Sales Coach AI",
                    "description": "Multi-agent sales coaching platform with real-time assistance",
                    "complexity": "high",
                    "expected_users": 1000,
                    "usage_patterns": {
                        "sessions_per_user_month": 20,
                        "avg_session_duration_minutes": 15,
                        "peak_concurrency_ratio": 0.1
                    }
                },
                "agents": [
                    {
                        "name": "CoachingAgent",
                        "role": "primary_coach",
                        "llm_config": {
                            "name": "gpt-4-turbo",
                            "provider": "openai",
                            "deployment_mode": "api"
                        },
                        "tools": [
                            {
                                "name": "crm_integration",
                                "type": "api",
                                "usage_frequency": "frequent"
                            }
                        ],
                        "complexity": "high",
                        "interaction_frequency": "continuous"
                    }
                ],
                "infrastructure": {
                    "deployment_type": "cloud",
                    "cloud_provider": "aws",
                    "region": "us-east-1",
                    "scaling_strategy": "auto",
                    "availability_requirement": 99.9
                }
            }
        }


class CostEstimationRequest(BaseModel):
    """Request for cost estimation."""
    specification: ApplicationSpecification = Field(description="Application specification")
    estimation_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional estimation options"
    )
    scenario_analysis: bool = Field(
        default=True,
        description="Whether to perform scenario analysis"
    )
    optimization_suggestions: bool = Field(
        default=True,
        description="Whether to include optimization suggestions"
    )


# Utility functions for schema validation and enhancement
def validate_specification(spec_dict: Dict[str, Any]) -> ApplicationSpecification:
    """Validate and parse application specification."""
    return ApplicationSpecification(**spec_dict)


def enrich_specification(spec: ApplicationSpecification) -> ApplicationSpecification:
    """Enrich specification with intelligent defaults and inferences."""
    # This would be implemented by an agent to add intelligent defaults
    # based on application patterns and industry best practices
    return spec