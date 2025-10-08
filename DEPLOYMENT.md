# Deployment Guide for Cost Estimator AI Agent

This guide provides step-by-step instructions for deploying the Cost Estimator AI Agent in various environments, from local development to production cloud deployment.

## 🎯 Deployment Overview

The Cost Estimator AI Agent supports multiple deployment strategies:

- **Local Development**: Direct Python execution
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-service orchestration
- **Cloud Platforms**: AWS, Azure, GCP
- **Kubernetes**: Container orchestration
- **Serverless**: Functions-as-a-Service

## 🔧 Prerequisites

### Required Tools

- Python 3.11+
- Docker and Docker Compose
- Git
- Cloud CLI tools (if deploying to cloud)

### Required Credentials

- At least one LLM API key (OpenAI, Anthropic, or Azure OpenAI)
- Cloud provider credentials (for live pricing and deployment)
- SSL certificates (for production HTTPS)

## 🚀 Local Development Deployment

### Quick Start

```bash
# Clone and setup
git clone https://github.com/rajfnu/cost-estimator-agent.git
cd cost-estimator-agent

# Install dependencies
make dev-install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
make serve
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install package
pip install -e ".[dev]"

# Run server
uvicorn cost_estimator.api:app --reload --host 0.0.0.0 --port 8000
```

### Verification

```bash
# Check API health
curl http://localhost:8000/health

# Test estimation
python -m cost_estimator.cli estimate --input examples/minimal_example.json
```

## 🐳 Docker Deployment

### Single Container Deployment

```bash
# Build image
docker build -t cost-estimator-agent .

# Run container
docker run -d \
  --name cost-estimator \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/data:/app/data \
  cost-estimator-agent

# Check logs
docker logs cost-estimator

# Test deployment
curl http://localhost:8000/health
```

### Docker Compose Deployment

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs cost-estimator

# Scale API service
docker-compose up -d --scale cost-estimator=3

# Stop services
docker-compose down
```

### Production Docker Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  cost-estimator:
    build:
      context: .
      target: production
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - cost-estimator

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cost_estimator
      POSTGRES_USER: cost_estimator
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Deploy with:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### AWS ECS (Elastic Container Service)

1. **Build and Push to ECR**

```bash
# Create ECR repository
aws ecr create-repository --repository-name cost-estimator-agent

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t cost-estimator-agent .
docker tag cost-estimator-agent:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cost-estimator-agent:latest

# Push image
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cost-estimator-agent:latest
```

2. **Create ECS Task Definition**

Create `ecs-task-definition.json`:

```json
{
  "family": "cost-estimator-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "cost-estimator",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/cost-estimator-agent:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:cost-estimator/openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cost-estimator-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

3. **Deploy with ECS Service**

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service \
  --cluster your-cluster \
  --service-name cost-estimator-agent \
  --task-definition cost-estimator-agent \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef],assignPublicIp=ENABLED}"
```

#### AWS Lambda (Serverless)

Create `serverless.yml`:

```yaml
service: cost-estimator-agent

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  environment:
    OPENAI_API_KEY: ${ssm:/cost-estimator/openai-key}
    DATABASE_URL: ${ssm:/cost-estimator/database-url}

functions:
  api:
    handler: cost_estimator.lambda_handler.handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
    timeout: 30
    memorySize: 1024

plugins:
  - serverless-python-requirements
```

Deploy with:

```bash
# Install Serverless Framework
npm install -g serverless

# Deploy
serverless deploy
```

### Azure Deployment

#### Azure Container Instances

```bash
# Create resource group
az group create --name cost-estimator-rg --location eastus

# Create container instance
az container create \
  --resource-group cost-estimator-rg \
  --name cost-estimator \
  --image your-registry.azurecr.io/cost-estimator-agent:latest \
  --dns-name-label cost-estimator-app \
  --ports 8000 \
  --environment-variables ENVIRONMENT=production \
  --secure-environment-variables OPENAI_API_KEY=$OPENAI_API_KEY \
  --cpu 1 \
  --memory 2
```

#### Azure App Service

Create `azure-pipelines.yml`:

```yaml
trigger:
- main

variables:
  dockerRegistryServiceConnection: 'your-acr-connection'
  imageRepository: 'cost-estimator-agent'
  containerRegistry: 'yourregistry.azurecr.io'
  tag: '$(Build.BuildId)'

stages:
- stage: Build
  jobs:
  - job: Build
    pool:
      vmImage: ubuntu-latest
    steps:
    - task: Docker@2
      displayName: 'Build and push image'
      inputs:
        command: 'buildAndPush'
        repository: $(imageRepository)
        dockerfile: 'Dockerfile'
        containerRegistry: $(dockerRegistryServiceConnection)
        tags: |
          $(tag)
          latest

- stage: Deploy
  jobs:
  - job: Deploy
    pool:
      vmImage: ubuntu-latest
    steps:
    - task: AzureWebAppContainer@1
      displayName: 'Deploy to Azure Web App'
      inputs:
        azureSubscription: 'your-azure-subscription'
        appName: 'cost-estimator-app'
        containers: $(containerRegistry)/$(imageRepository):$(tag)
```

### Google Cloud Platform Deployment

#### Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/cost-estimator-agent

# Deploy to Cloud Run
gcloud run deploy cost-estimator-agent \
  --image gcr.io/$PROJECT_ID/cost-estimator-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets OPENAI_API_KEY=openai-key:latest \
  --memory 2Gi \
  --cpu 1 \
  --max-instances 10
```

#### Google Kubernetes Engine (GKE)

Create Kubernetes manifests:

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-estimator-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cost-estimator-agent
  template:
    metadata:
      labels:
        app: cost-estimator-agent
    spec:
      containers:
      - name: cost-estimator
        image: gcr.io/PROJECT_ID/cost-estimator-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: cost-estimator-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: cost-estimator-service
spec:
  selector:
    app: cost-estimator-agent
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
# Create GKE cluster
gcloud container clusters create cost-estimator-cluster \
  --num-nodes 3 \
  --machine-type e2-medium \
  --region us-central1

# Deploy application
kubectl apply -f deployment.yaml

# Get external IP
kubectl get service cost-estimator-service
```

## 🎛️ Kubernetes Deployment

### Helm Chart Deployment

Create `helm/cost-estimator/values.yaml`:

```yaml
replicaCount: 3

image:
  repository: cost-estimator-agent
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: cost-estimator-tls
      hosts:
        - api.yourdomain.com

env:
  ENVIRONMENT: production
  DEBUG: false

secrets:
  OPENAI_API_KEY: your-openai-key
  ANTHROPIC_API_KEY: your-anthropic-key

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true
  auth:
    postgresPassword: your-postgres-password
    database: cost_estimator

redis:
  enabled: true
  auth:
    enabled: false
```

Deploy with Helm:

```bash
# Add Helm repository
helm repo add bitnami https://charts.bitnami.com/bitnami

# Install dependencies
helm dependency update helm/cost-estimator

# Deploy
helm install cost-estimator helm/cost-estimator \
  --namespace cost-estimator \
  --create-namespace \
  --values helm/cost-estimator/values.yaml
```

## 🔒 Production Security Configuration

### SSL/TLS Configuration

#### Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
upstream cost_estimator {
    server cost-estimator:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://cost_estimator;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://cost_estimator/health;
        access_log off;
    }
}
```

#### Let's Encrypt Certificate

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Secret Management

#### AWS Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
  --name "cost-estimator/openai-key" \
  --description "OpenAI API key for Cost Estimator" \
  --secret-string "your-openai-api-key"

# Create IAM role for ECS task
aws iam create-role \
  --role-name cost-estimator-task-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policy for secrets access
aws iam attach-role-policy \
  --role-name cost-estimator-task-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

#### Kubernetes Secrets

```bash
# Create secret
kubectl create secret generic cost-estimator-secrets \
  --from-literal=openai-api-key=your-openai-key \
  --from-literal=anthropic-api-key=your-anthropic-key

# Use in deployment
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: cost-estimator-secrets
type: Opaque
stringData:
  openai-api-key: your-openai-key
  anthropic-api-key: your-anthropic-key
EOF
```

## 📊 Monitoring and Observability

### Prometheus Monitoring

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cost-estimator'
    static_configs:
      - targets: ['cost-estimator:9090']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
```

### Grafana Dashboards

Create `monitoring/grafana/dashboards/cost-estimator.json`:

```json
{
  "dashboard": {
    "title": "Cost Estimator Agent",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

Create `logging/fluentd.conf`:

```conf
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<match cost_estimator.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name cost_estimator
  type_name _doc
</match>
```

## 🔧 Deployment Automation

### GitHub Actions CI/CD

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Cost Estimator Agent

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[test]"
    - name: Run tests
      run: pytest tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to production
      run: |
        # Add your deployment commands here
        echo "Deploying to production..."
```

### Terraform Infrastructure

Create `terraform/main.tf`:

```hcl
provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "cost_estimator" {
  name = "cost-estimator-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "cost_estimator" {
  name            = "cost-estimator-service"
  cluster         = aws_ecs_cluster.cost_estimator.id
  task_definition = aws_ecs_task_definition.cost_estimator.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.subnet_ids
    security_groups = [aws_security_group.cost_estimator.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cost_estimator.arn
    container_name   = "cost-estimator"
    container_port   = 8000
  }
}

# Additional resources...
```

Deploy with Terraform:

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply changes
terraform apply
```

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] API keys securely stored
- [ ] SSL certificates obtained
- [ ] Database migrations run
- [ ] Health checks configured
- [ ] Monitoring setup
- [ ] Backup strategy in place

### Deployment

- [ ] Build and test Docker image
- [ ] Deploy to staging environment
- [ ] Run integration tests
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Test critical paths

### Post-Deployment

- [ ] Monitor application metrics
- [ ] Check error logs
- [ ] Verify external integrations
- [ ] Test API endpoints
- [ ] Document deployment
- [ ] Update runbooks

## 🔧 Troubleshooting

### Common Issues

1. **Container Won't Start**
```bash
# Check logs
docker logs cost-estimator

# Check configuration
docker exec -it cost-estimator env | grep -E "(OPENAI|DEBUG)"
```

2. **Health Check Failures**
```bash
# Test health endpoint
curl -v http://localhost:8000/health

# Check application logs
kubectl logs deployment/cost-estimator-agent
```

3. **Database Connection Issues**
```bash
# Test database connectivity
docker exec -it postgres psql -U cost_estimator -d cost_estimator -c "SELECT 1;"
```

4. **API Key Issues**
```bash
# Verify API key configuration
python -c "
from cost_estimator.config import get_config
config = get_config()
print('OpenAI configured:', bool(config.llm.openai_api_key))
"
```

This comprehensive deployment guide ensures you can successfully deploy the Cost Estimator AI Agent in any environment, from development to production scale.