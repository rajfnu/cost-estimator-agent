# Configuration Guide for Cost Estimator AI Agent

This guide provides detailed information about configuring the Cost Estimator AI Agent for different environments and use cases.

## 📁 Configuration Files

### Primary Configuration Files

1. **`.env`** - Environment variables and secrets
2. **`pyproject.toml`** - Project metadata and dependencies
3. **`docker-compose.yml`** - Container orchestration
4. **`Dockerfile`** - Container build instructions

### Configuration Hierarchy

The system reads configuration in this order (later values override earlier ones):

1. Default values in `config.py`
2. `.env` file in project root
3. Environment variables
4. Command-line arguments (where applicable)

## 🔧 Environment Variables

### Core Application Settings

```bash
# Application Identity
APP_NAME="Cost Estimator Agent"
APP_VERSION="0.1.0"
DEBUG=false
ENVIRONMENT=development  # development, staging, production

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text
```

### LLM Provider Configuration

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_RATE_LIMIT_RPM=500

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEFAULT_ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_RATE_LIMIT_RPM=300

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
```

### Cloud Provider Credentials

```bash
# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Azure
AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret

# Google Cloud Platform
GCP_PROJECT_ID=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/gcp-service-account.json
```

### Pricing Configuration

```bash
# Pricing Data Management
PRICING_CACHE_TTL_HOURS=24
PRICING_REFRESH_INTERVAL_MINUTES=60
ENABLE_LIVE_PRICING=true
FALLBACK_TO_CACHED_PRICING=true

# Custom Pricing Sources
CUSTOM_PRICING_API_URL=https://your-custom-pricing-api.com
CUSTOM_PRICING_API_KEY=your_custom_pricing_api_key
```

### Database Configuration

```bash
# Primary Database
DATABASE_URL=sqlite:///./data/cost_estimator.db
# For PostgreSQL: postgresql://user:password@localhost:5432/cost_estimator

# Redis (for caching)
REDIS_URL=redis://localhost:6379

# Connection Pool Settings
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### Security Settings

```bash
# Application Security
SECRET_KEY=your-secret-key-change-this-in-production-32-chars-minimum
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,https://your-frontend.com

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

### Observability Configuration

```bash
# Metrics and Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# LangFuse (LangChain Observability)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Feature Flags

```bash
# Core Features
ENABLE_OPTIMIZATION_SUGGESTIONS=true
ENABLE_SCENARIO_ANALYSIS=true
ENABLE_COMPARATIVE_ANALYSIS=true
ENABLE_REAL_TIME_PRICING=true

# Experimental Features
ENABLE_STREAMING_ESTIMATION=false
ENABLE_COST_ALERTS=false
ENABLE_ML_PREDICTIONS=false
```

## 🌍 Environment-Specific Configurations

### Development Environment

Create `.env.development`:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Use local/cached data to avoid API costs
ENABLE_LIVE_PRICING=false
FALLBACK_TO_CACHED_PRICING=true

# Relaxed security for development
SECRET_KEY=development-secret-key-not-for-production
CORS_ORIGINS=*

# Local database
DATABASE_URL=sqlite:///./data/cost_estimator_dev.db
```

### Staging Environment

Create `.env.staging`:

```bash
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=staging

# Enable live pricing for testing
ENABLE_LIVE_PRICING=true
FALLBACK_TO_CACHED_PRICING=true

# Staging security
SECRET_KEY=staging-secret-key-32-characters-minimum
ALLOWED_HOSTS=staging.your-domain.com
CORS_ORIGINS=https://staging-frontend.your-domain.com

# Staging database
DATABASE_URL=postgresql://user:password@staging-db:5432/cost_estimator_staging
```

### Production Environment

Create `.env.production`:

```bash
DEBUG=false
LOG_LEVEL=WARNING
ENVIRONMENT=production

# Full live pricing
ENABLE_LIVE_PRICING=true
FALLBACK_TO_CACHED_PRICING=true

# Production security (use secrets management)
SECRET_KEY=${SECRET_KEY}  # From secret store
ALLOWED_HOSTS=api.your-domain.com
CORS_ORIGINS=https://your-domain.com

# Production database with connection pooling
DATABASE_URL=postgresql://user:password@prod-db:5432/cost_estimator
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50

# Enhanced monitoring
ENABLE_METRICS=true
LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
```

## 🐳 Docker Configuration

### Environment Variables in Docker

**Method 1: Environment file**
```bash
# Create .env.docker
echo "OPENAI_API_KEY=your_key" > .env.docker

# Run with environment file
docker run --env-file .env.docker cost-estimator-agent
```

**Method 2: Direct environment variables**
```bash
docker run -e OPENAI_API_KEY=your_key \
           -e DEBUG=true \
           cost-estimator-agent
```

**Method 3: Docker Compose with environment**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  cost-estimator:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=true
    env_file:
      - .env.local
```

### Volume Mounts for Configuration

```bash
# Mount configuration files
docker run -v $(pwd)/.env:/app/.env \
           -v $(pwd)/data:/app/data \
           cost-estimator-agent
```

## ⚙️ Advanced Configuration

### Custom Pricing Sources

Configure custom pricing APIs:

```bash
# Custom pricing configuration
CUSTOM_PRICING_API_URL=https://your-pricing-api.com/v1
CUSTOM_PRICING_API_KEY=your_api_key
CUSTOM_PRICING_REFRESH_MINUTES=30

# Pricing source priority (comma-separated)
PRICING_SOURCE_PRIORITY=custom,aws_pricing_api,azure_pricing_api,cached
```

### Model Configuration

Customize default models for different use cases:

```bash
# Default models by complexity
DEFAULT_MODEL_LOW_COMPLEXITY=gpt-3.5-turbo
DEFAULT_MODEL_MEDIUM_COMPLEXITY=gpt-4-turbo-preview
DEFAULT_MODEL_HIGH_COMPLEXITY=claude-3-opus-20240229

# Model fallback chain
MODEL_FALLBACK_CHAIN=gpt-4-turbo,claude-3-sonnet,gpt-3.5-turbo
```

### Regional Configuration

Configure different settings by region:

```bash
# Primary region
PRIMARY_REGION=us-east-1

# Region-specific pricing
ENABLE_REGIONAL_PRICING=true
SUPPORTED_REGIONS=us-east-1,us-west-2,eu-west-1,ap-southeast-1

# Fallback region for pricing
FALLBACK_PRICING_REGION=us-east-1
```

## 🔒 Security Configuration

### Production Security Checklist

1. **Generate Strong Secret Key**
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Configure HTTPS**
```bash
# SSL/TLS configuration
SSL_CERT_PATH=/path/to/your/certificate.pem
SSL_KEY_PATH=/path/to/your/private-key.pem
FORCE_HTTPS=true
```

3. **API Key Security**
```bash
# Use environment variables or secret management
# Never commit API keys to version control
OPENAI_API_KEY=${OPENAI_API_KEY}  # From AWS Secrets Manager, etc.
```

4. **Network Security**
```bash
# Restrict allowed hosts
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com

# Configure CORS properly
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Secret Management Integration

**AWS Secrets Manager**
```bash
# Use AWS CLI to fetch secrets
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id "prod/cost-estimator/openai-key" \
  --query SecretString --output text)
```

**Azure Key Vault**
```bash
# Use Azure CLI to fetch secrets
export OPENAI_API_KEY=$(az keyvault secret show \
  --vault-name "cost-estimator-vault" \
  --name "openai-key" \
  --query value --output tsv)
```

**HashiCorp Vault**
```bash
# Use Vault CLI to fetch secrets
export OPENAI_API_KEY=$(vault kv get -field=api_key secret/cost-estimator/openai)
```

## 📊 Monitoring Configuration

### Prometheus Metrics

```bash
# Enable metrics collection
ENABLE_METRICS=true
METRICS_PORT=9090
METRICS_PATH=/metrics

# Custom metric labels
METRICS_LABELS=environment:production,service:cost-estimator
```

### Logging Configuration

```bash
# Structured logging
LOG_FORMAT=json
LOG_LEVEL=INFO

# Log destinations
LOG_FILE=/app/logs/cost-estimator.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30

# Performance logging
ENABLE_PERFORMANCE_LOGGING=true
SLOW_QUERY_THRESHOLD_SECONDS=5
```

### Health Check Configuration

```bash
# Health check settings
HEALTH_CHECK_TIMEOUT_SECONDS=30
HEALTH_CHECK_INTERVAL_SECONDS=60

# Dependency health checks
ENABLE_DB_HEALTH_CHECK=true
ENABLE_REDIS_HEALTH_CHECK=true
ENABLE_LLM_HEALTH_CHECK=true
```

## 🔧 Troubleshooting Configuration

### Common Configuration Issues

1. **Missing API Keys**
```bash
# Validate API key configuration
python -c "
from cost_estimator.config import get_config
config = get_config()
issues = config.validate_required_keys(['openai', 'anthropic'])
if issues:
    print('Missing keys:', issues)
else:
    print('All required keys configured')
"
```

2. **Database Connection Issues**
```bash
# Test database connection
python -c "
from cost_estimator.config import get_config
from sqlalchemy import create_engine
config = get_config()
try:
    engine = create_engine(config.database.database_url)
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

3. **Configuration Validation**
```bash
# Validate complete configuration
python -c "
from cost_estimator.config import get_config, validate_configuration
config = get_config()
issues = validate_configuration(config)
if issues:
    print('Configuration issues:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('Configuration is valid')
"
```

### Debug Configuration Loading

```bash
# Enable configuration debugging
DEBUG_CONFIG=true python -m cost_estimator.cli --help

# Show effective configuration (without secrets)
python -c "
from cost_estimator.config import get_config
config = get_config()
print(f'Environment: {config.environment}')
print(f'Debug mode: {config.debug}')
print(f'API port: {config.api_port}')
print(f'Database URL: {config.database.database_url}')
"
```

## 📋 Configuration Templates

### Minimal Configuration Template

```bash
# .env.minimal
OPENAI_API_KEY=your_openai_key_here
SECRET_KEY=change-this-in-production-32-chars-minimum
```

### Development Configuration Template

```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
SECRET_KEY=development-secret-key-not-for-production
ENABLE_LIVE_PRICING=false
DATABASE_URL=sqlite:///./data/cost_estimator_dev.db
```

### Production Configuration Template

```bash
# .env.production
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=production
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql://user:password@db:5432/cost_estimator
REDIS_URL=redis://redis:6379
ENABLE_METRICS=true
LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
```

## 🔄 Configuration Management Best Practices

1. **Use Environment-Specific Files**: Separate configurations for dev/staging/prod
2. **Secret Management**: Never commit secrets; use environment variables or secret stores
3. **Validation**: Always validate configuration on startup
4. **Documentation**: Document all configuration options and their effects
5. **Defaults**: Provide sensible defaults for development
6. **Overrides**: Allow environment variables to override file-based config
7. **Monitoring**: Monitor configuration changes in production

This comprehensive configuration guide ensures you can deploy and run the Cost Estimator AI Agent in any environment with the appropriate settings for your use case.