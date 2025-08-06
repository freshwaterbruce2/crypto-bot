# 🚀 Production Deployment Guide - Crypto Trading Platform

## Overview

This guide provides step-by-step instructions for deploying the enterprise-grade crypto trading platform to production. The deployment uses Infrastructure as Code (IaC) with Terraform to ensure consistency and repeatability.

## Prerequisites

### Required Tools
- Terraform >= 1.3.0
- AWS CLI configured with appropriate credentials
- GCP CLI (gcloud) configured
- kubectl >= 1.28
- Helm >= 3.10
- Docker >= 20.10
- git

### Required Access
- AWS account with admin privileges
- GCP project with owner role
- Domain name with DNS management access
- Kraken API credentials (trade-only, no withdrawal)

## Deployment Steps

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/crypto-trading-bot-2025.git
cd crypto-trading-bot-2025/infrastructure/production-deployment

# Create terraform.tfvars from template
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your specific values
nano terraform.tfvars
```

### 2. Configure Secrets

```bash
# Set sensitive environment variables
export TF_VAR_kraken_api_key="your-api-key"
export TF_VAR_kraken_api_secret="your-api-secret"
export TF_VAR_source_db_password="your-db-password"
export TF_VAR_slack_webhook_url="your-webhook-url"
```

### 3. Initialize Terraform

```bash
# Initialize Terraform with remote state
terraform init

# Create workspace for production
terraform workspace new production
terraform workspace select production

# Validate configuration
terraform validate

# Plan deployment
terraform plan -out=production.tfplan
```

### 4. Deploy Infrastructure

```bash
# Apply in phases for safety

# Phase 1: Networking and Security
terraform apply -target=module.aws_networking -target=module.dr_networking
terraform apply -target=aws_kms_key.secrets -target=aws_kms_key.rds

# Phase 2: Databases and Storage
terraform apply -target=aws_rds_cluster.primary -target=aws_s3_bucket.backups_primary
terraform apply -target=aws_elasticache_replication_group.trading_cache

# Phase 3: Kubernetes Clusters
terraform apply -target=aws_eks_cluster.production -target=google_container_cluster.production

# Phase 4: Load Balancers and SSL
terraform apply -target=aws_lb.trading_api -target=aws_acm_certificate.trading_api
terraform apply -target=google_compute_global_address.trading_ip

# Phase 5: Complete Deployment
terraform apply production.tfplan
```

### 5. Configure Kubernetes

```bash
# Get EKS credentials
aws eks update-kubeconfig --name crypto-trading-production --region us-east-1

# Create namespaces
kubectl create namespace trading-system
kubectl create namespace monitoring
kubectl create namespace security

# Label namespaces for policies
kubectl label namespace trading-system network-policy-enforced=true
kubectl label namespace trading-system pod-security.kubernetes.io/enforce=restricted

# Apply RBAC policies
kubectl apply -f kubernetes/rbac/

# Install service mesh (optional but recommended)
kubectl apply -f https://github.com/istio/istio/releases/download/1.19.0/istio-1.19.0-linux-amd64.tar.gz
istioctl install --set profile=production
```

### 6. Deploy Application

```bash
# Build and push Docker images
docker build -t your-registry/crypto-trading-bot:latest .
docker push your-registry/crypto-trading-bot:latest

# Deploy using Helm
helm install crypto-trading ./helm/crypto-trading \
  --namespace trading-system \
  --values helm/crypto-trading/values-production.yaml \
  --set image.tag=latest \
  --set kraken.apiKey=$TF_VAR_kraken_api_key \
  --set kraken.apiSecret=$TF_VAR_kraken_api_secret

# Verify deployment
kubectl -n trading-system get pods
kubectl -n trading-system get svc
```

### 7. Configure Monitoring

```bash
# Install Prometheus and Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring/prometheus-values.yaml

# Configure CloudWatch Container Insights
aws eks associate-addon \
  --cluster-name crypto-trading-production \
  --addon-name amazon-cloudwatch-observability \
  --service-account-role-arn $CLOUDWATCH_ROLE_ARN
```

### 8. Verify Deployment

```bash
# Run smoke tests
./scripts/smoke-tests.sh

# Check health endpoints
curl -k https://api.your-domain.com/health
curl -k https://api.your-domain.com/ready

# Verify WebSocket connectivity
wscat -c wss://ws.your-domain.com/v2/marketdata

# Check compliance status
aws securityhub get-compliance-summary
```

### 9. Enable Production Traffic

```bash
# Update DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch file://dns-changes.json

# Enable WAF rules
aws wafv2 update-web-acl \
  --scope CLOUDFRONT \
  --id $WAF_ID \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Start with limited traffic
kubectl -n trading-system scale deployment crypto-trading --replicas=3

# Monitor for 1 hour, then scale up
kubectl -n trading-system scale deployment crypto-trading --replicas=10
```

### 10. Post-Deployment

```bash
# Enable automated backups
kubectl apply -f backup/velero-schedule.yaml

# Configure alerts
./scripts/configure-alerts.sh

# Document deployment
./scripts/generate-deployment-report.sh > deployment-report.md
```

## Rollback Procedures

If issues arise during deployment:

```bash
# Immediate rollback
terraform workspace select production
terraform plan -destroy -out=rollback.tfplan
terraform apply rollback.tfplan

# Or selective rollback
terraform state list
terraform destroy -target=<specific-resource>

# Application rollback
helm rollback crypto-trading 1 -n trading-system
```

## Maintenance

### Daily Tasks
- Review CloudWatch dashboards
- Check compliance reports
- Monitor cost optimization recommendations

### Weekly Tasks
- Review security findings
- Update dependencies
- Performance tuning

### Monthly Tasks
- Disaster recovery drill
- Security patching
- Cost optimization review

## Troubleshooting

### Common Issues

1. **SSL Certificate Validation Failure**
   ```bash
   aws acm describe-certificate --certificate-arn $CERT_ARN
   # Check DNS validation records
   ```

2. **Database Connection Issues**
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier crypto-trading-primary
   # Check security groups and network ACLs
   ```

3. **Kubernetes Pod Failures**
   ```bash
   kubectl -n trading-system describe pod <pod-name>
   kubectl -n trading-system logs <pod-name> --previous
   ```

## Support

- **Infrastructure Issues**: infrastructure-team@company.com
- **Application Issues**: platform-team@company.com
- **Security Issues**: security-team@company.com
- **24/7 Hotline**: +1-XXX-XXX-XXXX

## Appendix

### A. Environment Variables Reference
See `terraform.tfvars.example` for all configurable values.

### B. Architecture Diagrams
Located in `docs/architecture/`

### C. Compliance Documentation
Located in `docs/compliance/`

### D. Disaster Recovery Runbooks
Located in `docs/disaster-recovery/`

---

**Remember: Always test in staging before production deployment!**