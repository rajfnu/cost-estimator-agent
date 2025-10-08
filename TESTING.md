# Testing Guide for Cost Estimator AI Agent

This guide provides comprehensive instructions for testing the Cost Estimator AI Agent across different environments and scenarios.

## 🚀 Quick Start Testing

### Prerequisites
- Python 3.11+
- Git
- Optional: Docker & Docker Compose

### 1. Clone and Set Up

```bash
# Clone the repository
git clone https://github.com/rajfnu/cost-estimator-agent.git
cd cost-estimator-agent

# Quick setup using Makefile
make dev-setup

# OR manual setup
pip install -e .
cp .env.example .env
# Edit .env with your API keys (see Configuration section below)
```

### 2. Verify Installation

```bash
# Check installation
make validate
# OR
python scripts/setup.py validate

# Run basic tests
make test-unit
```

## 🔑 Configuration

### Required API Keys

For full functionality, add these to your `.env` file:

```bash
# At least one LLM API key is required for cost estimation
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional but recommended

# Optional: Cloud provider credentials for live pricing
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
GCP_PROJECT_ID=your_gcp_project_id
```

### Development vs Production

```bash
# Development (default)
DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_LIVE_PRICING=false

# Production
DEBUG=false
LOG_LEVEL=INFO
ENABLE_LIVE_PRICING=true
SECRET_KEY=your-very-secure-secret-key-32-chars-minimum
```

## 🧪 Testing Scenarios

### Level 1: Basic Functionality (No API Keys Required)

These tests work without any API keys:

```bash
# 1. Schema Validation
python -m cost_estimator.cli validate examples/minimal_example.json
python -m cost_estimator.cli validate examples/sales_coach_app.json
python -m cost_estimator.cli validate examples/customer_support_bot.json
python -m cost_estimator.cli validate examples/content_generator.json

# 2. CLI Help and Structure
python -m cost_estimator.cli --help
python -m cost_estimator.cli validate --help
python -m cost_estimator.cli estimate --help

# 3. API Health Check
uvicorn cost_estimator.api:app --reload &
curl http://localhost:8000/health
curl http://localhost:8000/providers
curl http://localhost:8000/templates
```

**Expected Results:**
- ✅ All validation commands should pass
- ✅ Help commands show rich CLI interface
- ✅ API health endpoint returns status and supported providers

### Level 2: Cost Estimation (Requires LLM API Keys)

```bash
# 1. Basic Cost Estimation
python -m cost_estimator.cli estimate --input examples/minimal_example.json

# 2. Different Output Formats
python -m cost_estimator.cli estimate --input examples/sales_coach_app.json --format table
python -m cost_estimator.cli estimate --input examples/sales_coach_app.json --format json
python -m cost_estimator.cli estimate --input examples/sales_coach_app.json --format markdown

# 3. Scenario Comparison
python -m cost_estimator.cli compare examples/

# 4. API Estimation
curl -X POST http://localhost:8000/estimate \
  -H "Content-Type: application/json" \
  -d @examples/minimal_example.json
```

**Expected Results:**
- ✅ Cost estimates with reasonable monthly costs
- ✅ Optimization suggestions provided
- ✅ Confidence scores between 0.0-1.0
- ✅ Different output formats work correctly

### Level 3: Advanced Features (Full Configuration)

```bash
# 1. Scenario Analysis
python -m cost_estimator.cli estimate --input examples/content_generator.json --scenarios

# 2. Custom Application Creation
python -m cost_estimator.cli init "My Custom App" --template sales_coach
python -m cost_estimator.cli estimate --input my_custom_app_spec.json

# 3. API Advanced Features
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"scenario1": {...}, "scenario2": {...}}'
```

## 🐳 Docker Testing

### Basic Docker Testing

```bash
# 1. Build and test image
docker build -t cost-estimator-agent .

# 2. Run with environment file
docker run -p 8000:8000 -v $(pwd)/.env:/app/.env cost-estimator-agent

# 3. Test the containerized API
curl http://localhost:8000/health
```

### Docker Compose Testing

```bash
# 1. Full stack with dependencies
docker-compose up

# 2. Test with Redis and PostgreSQL
curl http://localhost:8000/health

# 3. CLI testing in container
docker-compose run cli estimate --input examples/minimal_example.json

# 4. Development mode
BUILD_TARGET=development docker-compose up
```

## 🧪 Test Suite Execution

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test files
pytest tests/unit/test_schemas.py -v
pytest tests/unit/test_graph.py -v

# Run with coverage
pytest tests/unit/ --cov=src/cost_estimator --cov-report=html
```

### Integration Tests (Future)

```bash
# When implemented
pytest tests/integration/ -v
```

### End-to-End Tests (Future)

```bash
# When implemented
pytest tests/e2e/ -v
```

## 📊 Performance Testing

### Basic Performance Checks

```bash
# 1. Time estimation for different complexity levels
time python -m cost_estimator.cli estimate --input examples/minimal_example.json
time python -m cost_estimator.cli estimate --input examples/content_generator.json

# 2. Memory usage monitoring
/usr/bin/time -v python -m cost_estimator.cli estimate --input examples/sales_coach_app.json

# 3. Concurrent API requests
# Install hey: brew install hey (macOS) or apt install hey (Ubuntu)
hey -n 100 -c 10 http://localhost:8000/health
```

### Load Testing (Future)

```bash
# When implemented with tools like locust
locust --host=http://localhost:8000
```

## 🔍 Debugging and Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors

```bash
# Issue: ModuleNotFoundError
# Solution: Ensure package is installed in development mode
pip install -e .

# Verify installation
python -c "import cost_estimator; print(cost_estimator.__version__)"
```

#### 2. API Key Issues

```bash
# Issue: LLM API calls failing
# Solution: Check API key configuration
python -c "
from cost_estimator.config import get_config
config = get_config()
print('OpenAI Key:', 'SET' if config.llm.openai_api_key else 'NOT SET')
print('Anthropic Key:', 'SET' if config.llm.anthropic_api_key else 'NOT SET')
"
```

#### 3. Docker Issues

```bash
# Issue: Docker build fails
# Solution: Check Docker version and build context
docker --version
docker build --no-cache -t cost-estimator-agent .

# Issue: Container can't access .env
# Solution: Verify volume mount
docker run -v $(pwd)/.env:/app/.env cost-estimator-agent env | grep -E "(OPENAI|ANTHROPIC)"
```

### Verbose Debugging

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m cost_estimator.cli estimate --input examples/sales_coach_app.json --verbose

# API debug mode
uvicorn cost_estimator.api:app --reload --log-level debug
```

## 📋 Test Checklist

Use this checklist to ensure comprehensive testing:

### ✅ Installation & Setup
- [ ] Fresh clone from GitHub works
- [ ] Dependencies install without errors
- [ ] `.env` file created and configured
- [ ] Basic validation commands work

### ✅ Core Functionality
- [ ] Schema validation passes for all examples
- [ ] CLI commands work with proper help text
- [ ] API health endpoint responds correctly
- [ ] Cost estimation produces reasonable results

### ✅ Output Formats
- [ ] Markdown format displays properly
- [ ] JSON format is valid and complete
- [ ] Table format is readable and aligned
- [ ] File output works correctly

### ✅ Error Handling
- [ ] Invalid JSON files are rejected gracefully
- [ ] Missing API keys produce helpful error messages
- [ ] Malformed requests return appropriate HTTP status codes
- [ ] Network failures are handled gracefully

### ✅ Docker Deployment
- [ ] Docker image builds successfully
- [ ] Container runs and serves API
- [ ] Environment variables passed correctly
- [ ] Health checks work in container

### ✅ Performance
- [ ] Estimation completes within reasonable time (< 30s)
- [ ] Memory usage stays within acceptable limits
- [ ] API responds quickly to health checks
- [ ] Multiple concurrent requests handled properly

## 🚀 Continuous Integration Testing

For automated testing in CI/CD pipelines:

```bash
# Install dependencies
make ci-install

# Run test suite
make ci-test

# Run linting and type checks
make ci-lint

# Validate examples
make validate-examples
```

## 🔮 Future Testing Phases

As development continues, these testing areas will be expanded:

1. **Integration Tests**: Real API calls to cloud providers
2. **End-to-End Tests**: Full workflow testing with actual data
3. **Performance Tests**: Load testing and benchmarking
4. **Security Tests**: Vulnerability scanning and penetration testing
5. **Compatibility Tests**: Different Python versions and platforms

## 📞 Getting Help

If you encounter issues during testing:

1. Check the [README.md](README.md) for general information
2. Review the [Configuration Guide](CONFIGURATION.md) for setup details
3. Look at the example files in `examples/` for reference
4. Check the logs with `DEBUG=true` for detailed error information
5. Create an issue on GitHub with detailed reproduction steps

## 📊 Expected Test Results

### Successful Test Outputs

**CLI Validation:**
```
🔍 Specification Validator

✅ Specification is valid!
```

**Cost Estimation:**
```
🤖 AI Multi-Agent Cost Estimator

📊 Analyzing: Sales Coach AI

💰 Cost Summary
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric             ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Total Monthly Cost │ $2,847.50   │
│ Confidence Score   │ 85.3%       │
│ Potential Savings  │ $431.20     │
└────────────────────┴─────────────┘
```

**API Health Check:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-08T21:30:00Z",
  "version": "0.1.0",
  "supported_providers": {
    "llm_providers": ["openai", "anthropic", "azure_openai"],
    "cloud_providers": ["aws", "azure", "gcp"],
    "vector_db_providers": ["pinecone", "weaviate", "qdrant"]
  }
}
```

These outputs indicate the system is working correctly and ready for production use!