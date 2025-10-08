"""
Configuration management for the Cost Estimator Agent.

Handles environment variables, settings validation, and configuration
for different deployment environments (development, staging, production).
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
try:
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator


class LLMConfig(BaseSettings):
    """Configuration for LLM providers."""

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")

    # Default models for different providers
    default_openai_model: str = Field(default="gpt-4-turbo-preview", env="DEFAULT_OPENAI_MODEL")
    default_anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="DEFAULT_ANTHROPIC_MODEL")

    # Rate limiting
    openai_rate_limit_rpm: int = Field(default=500, env="OPENAI_RATE_LIMIT_RPM")
    anthropic_rate_limit_rpm: int = Field(default=300, env="ANTHROPIC_RATE_LIMIT_RPM")


class CloudConfig(BaseSettings):
    """Configuration for cloud provider credentials."""

    # AWS
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")

    # Azure
    azure_subscription_id: Optional[str] = Field(default=None, env="AZURE_SUBSCRIPTION_ID")
    azure_tenant_id: Optional[str] = Field(default=None, env="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, env="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, env="AZURE_CLIENT_SECRET")

    # Google Cloud Platform
    gcp_project_id: Optional[str] = Field(default=None, env="GCP_PROJECT_ID")
    google_application_credentials: Optional[str] = Field(
        default=None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )


class PricingConfig(BaseSettings):
    """Configuration for pricing data management."""

    pricing_cache_ttl_hours: int = Field(default=24, env="PRICING_CACHE_TTL_HOURS")
    pricing_refresh_interval_minutes: int = Field(default=60, env="PRICING_REFRESH_INTERVAL_MINUTES")
    enable_live_pricing: bool = Field(default=True, env="ENABLE_LIVE_PRICING")
    fallback_to_cached_pricing: bool = Field(default=True, env="FALLBACK_TO_CACHED_PRICING")

    # Custom pricing sources
    custom_pricing_api_url: Optional[str] = Field(default=None, env="CUSTOM_PRICING_API_URL")
    custom_pricing_api_key: Optional[str] = Field(default=None, env="CUSTOM_PRICING_API_KEY")

    @field_validator('pricing_cache_ttl_hours')
    def validate_cache_ttl(cls, v):
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError("Cache TTL must be between 1 and 168 hours")
        return v


class DatabaseConfig(BaseSettings):
    """Configuration for database connections."""

    database_url: str = Field(default="sqlite:///./cost_estimator.db", env="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")

    # Connection pool settings
    db_pool_size: int = Field(default=5, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")


class ObservabilityConfig(BaseSettings):
    """Configuration for monitoring and observability."""

    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    # LangFuse (LangChain observability)
    langfuse_public_key: Optional[str] = Field(default=None, env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = Field(default=None, env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", env="LANGFUSE_HOST")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text

    @field_validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class SecurityConfig(BaseSettings):
    """Configuration for security settings."""

    secret_key: str = Field(default="development-secret-key-change-in-production", env="SECRET_KEY")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")

    @field_validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @field_validator('allowed_hosts', 'cors_origins', mode='before')
    def parse_comma_separated(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',') if host.strip()]
        return v


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling functionality."""

    enable_optimization_suggestions: bool = Field(default=True, env="ENABLE_OPTIMIZATION_SUGGESTIONS")
    enable_scenario_analysis: bool = Field(default=True, env="ENABLE_SCENARIO_ANALYSIS")
    enable_comparative_analysis: bool = Field(default=True, env="ENABLE_COMPARATIVE_ANALYSIS")
    enable_real_time_pricing: bool = Field(default=True, env="ENABLE_REAL_TIME_PRICING")

    # Experimental features
    enable_streaming_estimation: bool = Field(default=False, env="ENABLE_STREAMING_ESTIMATION")
    enable_cost_alerts: bool = Field(default=False, env="ENABLE_COST_ALERTS")
    enable_ml_predictions: bool = Field(default=False, env="ENABLE_ML_PREDICTIONS")


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Core app settings
    app_name: str = Field(default="Cost Estimator Agent", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")

    # Component configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @field_validator('environment')
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v

    @field_validator('api_port')
    def validate_api_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError("API port must be between 1 and 65535")
        return v

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get all configured API keys for validation."""
        return {
            "openai": self.llm.openai_api_key,
            "anthropic": self.llm.anthropic_api_key,
            "azure_openai": self.llm.azure_openai_api_key,
            "aws": self.cloud.aws_access_key_id,
            "azure": self.cloud.azure_client_id,
            "gcp": self.cloud.gcp_project_id,
        }

    def validate_required_keys(self, providers: List[str]) -> List[str]:
        """Validate that required API keys are present for specified providers."""
        missing_keys = []
        api_keys = self.get_api_keys()

        for provider in providers:
            if provider in api_keys and not api_keys[provider]:
                missing_keys.append(f"{provider}_api_key")

        return missing_keys


def load_config(env_file: Optional[str] = None) -> AppConfig:
    """
    Load configuration from environment variables and .env file.

    Args:
        env_file: Optional path to .env file

    Returns:
        Configured AppConfig instance
    """
    if env_file:
        return AppConfig(_env_file=env_file)

    # Try to find .env file in common locations
    possible_env_files = [
        Path(".env"),
        Path("../.env"),
        Path("../../.env"),
        Path.home() / ".cost_estimator" / ".env"
    ]

    for env_path in possible_env_files:
        if env_path.exists():
            return AppConfig(_env_file=str(env_path))

    # No .env file found, use environment variables only
    return AppConfig()


def create_development_config() -> AppConfig:
    """Create a development configuration with sensible defaults."""
    return AppConfig(
        debug=True,
        environment="development",
        api_workers=1,
        log_level="DEBUG",
        enable_live_pricing=False,  # Use cached pricing in development
        fallback_to_cached_pricing=True
    )


def validate_configuration(config: AppConfig) -> List[str]:
    """
    Validate configuration and return list of issues.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages
    """
    issues = []

    # Check for production-specific requirements
    if config.is_production():
        if not config.security.secret_key or len(config.security.secret_key) < 32:
            issues.append("Production requires a strong secret key (32+ characters)")

        if config.debug:
            issues.append("Debug mode should be disabled in production")

        if not config.observability.langfuse_public_key:
            issues.append("Production should have observability configured")

    # Check API key availability for enabled features
    if config.features.enable_real_time_pricing:
        if not config.llm.openai_api_key and not config.llm.anthropic_api_key:
            issues.append("Real-time pricing requires at least one LLM API key")

    if config.pricing.enable_live_pricing:
        if not config.cloud.aws_access_key_id and not config.cloud.azure_subscription_id:
            issues.append("Live pricing requires cloud provider credentials")

    return issues


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(env_file: Optional[str] = None) -> AppConfig:
    """Reload the global configuration."""
    global _config
    _config = load_config(env_file)
    return _config