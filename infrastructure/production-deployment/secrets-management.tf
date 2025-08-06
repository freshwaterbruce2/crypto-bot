# Secrets Management Configuration
# Secure handling of API keys, private keys, and sensitive credentials

# AWS Secrets Manager for primary secrets storage
resource "aws_secretsmanager_secret" "kraken_api" {
  name                    = "crypto-trading/kraken-api"
  description            = "Kraken Exchange API credentials"
  recovery_window_in_days = 30
  
  rotation_rules {
    automatically_after_days = 30
  }
  
  replica {
    region = var.aws_secondary_region
    kms_key_id = aws_kms_key.secrets_secondary.arn
  }
  
  tags = {
    Name        = "kraken-api-credentials"
    Environment = "production"
    Compliance  = "pci-dss"
  }
}

resource "aws_secretsmanager_secret_version" "kraken_api" {
  secret_id = aws_secretsmanager_secret.kraken_api.id
  
  secret_string = jsonencode({
    api_key    = var.kraken_api_key
    api_secret = var.kraken_api_secret
    api_tier   = "pro"
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Database credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "crypto-trading/database"
  description            = "Database master credentials"
  recovery_window_in_days = 30
  
  rotation_rules {
    automatically_after_days = 90
  }
  
  tags = {
    Name        = "database-credentials"
    Environment = "production"
  }
}

# Lambda function for secrets rotation
resource "aws_lambda_function" "rotate_secrets" {
  filename         = "lambda-rotate-secrets.zip"
  function_name    = "crypto-trading-rotate-secrets"
  role            = aws_iam_role.lambda_rotation.arn
  handler         = "index.handler"
  source_code_hash = filebase64sha256("lambda-rotate-secrets.zip")
  runtime         = "python3.11"
  timeout         = 60
  
  environment {
    variables = {
      SECRETS_MANAGER_ENDPOINT = "https://secretsmanager.${var.aws_region}.amazonaws.com"
    }
  }
  
  vpc_config {
    subnet_ids         = module.aws_networking.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }
}

# AWS Systems Manager Parameter Store for non-sensitive config
resource "aws_ssm_parameter" "trading_config" {
  name  = "/crypto-trading/config/production"
  type  = "String"
  value = jsonencode({
    exchange             = "kraken"
    trading_pairs        = var.trading_pairs
    position_size_usdt   = var.position_size_usdt
    max_positions        = var.max_positions
    risk_percentage      = var.risk_percentage
  })
  
  tags = {
    Environment = "production"
  }
}

# HashiCorp Vault for additional secrets management
resource "helm_release" "vault" {
  name       = "vault"
  repository = "https://helm.releases.hashicorp.com"
  chart      = "vault"
  version    = "0.25.0"
  namespace  = "vault"
  
  create_namespace = true
  
  values = [
    <<-EOT
    global:
      enabled: true
      
    injector:
      enabled: true
      
    server:
      ha:
        enabled: true
        replicas: 3
        raft:
          enabled: true
          setNodeId: true
          
      auditStorage:
        enabled: true
        size: 10Gi
        
      dataStorage:
        enabled: true
        size: 10Gi
        
      resources:
        requests:
          memory: 256Mi
          cpu: 250m
        limits:
          memory: 512Mi
          cpu: 500m
          
    ui:
      enabled: true
      serviceType: "ClusterIP"
    EOT
  ]
}

# Kubernetes Secrets for application use
resource "kubernetes_secret" "kraken_api" {
  metadata {
    name      = "kraken-api-credentials"
    namespace = "trading-system"
  }
  
  type = "Opaque"
  
  data = {
    api_key    = base64encode(var.kraken_api_key)
    api_secret = base64encode(var.kraken_api_secret)
  }
}

# External Secrets Operator for syncing secrets
resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = "0.9.0"
  namespace  = "external-secrets"
  
  create_namespace = true
  
  set {
    name  = "installCRDs"
    value = "true"
  }
}

# SecretStore for AWS Secrets Manager
resource "kubernetes_manifest" "secret_store" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "SecretStore"
    metadata = {
      name      = "aws-secrets-manager"
      namespace = "trading-system"
    }
    spec = {
      provider = {
        aws = {
          service = "SecretsManager"
          region  = var.aws_region
          auth = {
            jwt = {
              serviceAccountRef = {
                name = "external-secrets-sa"
              }
            }
          }
        }
      }
    }
  }
  
  depends_on = [helm_release.external_secrets]
}

# External Secret for Kraken API
resource "kubernetes_manifest" "kraken_external_secret" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "ExternalSecret"
    metadata = {
      name      = "kraken-api"
      namespace = "trading-system"
    }
    spec = {
      refreshInterval = "1h"
      secretStoreRef = {
        name = "aws-secrets-manager"
        kind = "SecretStore"
      }
      target = {
        name = "kraken-api-credentials"
        creationPolicy = "Owner"
      }
      data = [
        {
          secretKey = "api_key"
          remoteRef = {
            key      = "crypto-trading/kraken-api"
            property = "api_key"
          }
        },
        {
          secretKey = "api_secret"
          remoteRef = {
            key      = "crypto-trading/kraken-api"
            property = "api_secret"
          }
        }
      ]
    }
  }
  
  depends_on = [kubernetes_manifest.secret_store]
}

# KMS Keys for encryption
resource "aws_kms_key" "secrets" {
  description             = "KMS key for secrets encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Secrets Manager"
        Effect = "Allow"
        Principal = {
          Service = "secretsmanager.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
  
  tags = {
    Name = "crypto-trading-secrets-key"
  }
}

# Sealed Secrets for GitOps
resource "helm_release" "sealed_secrets" {
  name       = "sealed-secrets"
  repository = "https://bitnami-labs.github.io/sealed-secrets"
  chart      = "sealed-secrets"
  version    = "2.13.0"
  namespace  = "kube-system"
  
  set {
    name  = "controller.create"
    value = "true"
  }
}

# Google Secret Manager (for GCP resources)
resource "google_secret_manager_secret" "kraken_api" {
  secret_id = "kraken-api-credentials"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = "production"
    compliance  = "pci-dss"
  }
}

resource "google_secret_manager_secret_version" "kraken_api" {
  secret = google_secret_manager_secret.kraken_api.id
  
  secret_data = jsonencode({
    api_key    = var.kraken_api_key
    api_secret = var.kraken_api_secret
  })
}

# Service Account for Workload Identity
resource "google_service_account" "workload_identity" {
  account_id   = "trading-workload-identity"
  display_name = "Trading Platform Workload Identity"
}

# IAM binding for Secret Manager access
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.kraken_api.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.workload_identity.email}"
}

# Kubernetes Service Account annotation for Workload Identity
resource "kubernetes_service_account" "trading" {
  metadata {
    name      = "trading-service"
    namespace = "trading-system"
    
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.workload_identity.email
    }
  }
}

# Secret scanning prevention
resource "github_repository_file" "gitleaks" {
  repository = var.github_repo_name
  branch     = "main"
  file       = ".gitleaks.toml"
  
  content = <<-EOT
  title = "Crypto Trading Bot Secret Scanning"
  
  [[rules]]
  description = "AWS Access Key"
  regex = '''AKIA[0-9A-Z]{16}'''
  tags = ["aws", "credentials"]
  
  [[rules]]
  description = "Private Key"
  regex = '''-----BEGIN (RSA|EC|DSA) PRIVATE KEY-----'''
  tags = ["key", "private"]
  
  [[rules]]
  description = "API Secret Pattern"
  regex = '''(api_secret|apiSecret|api-secret)["']?\s*[:=]\s*["']?[A-Za-z0-9/+=]{40,}'''
  tags = ["api", "secret"]
  
  [allowlist]
  paths = [
    '''.gitleaks.toml''',
    '''terraform.tfstate''',
    '''*.tfvars'''
  ]
  EOT
}

# Monitoring for secret access
resource "aws_cloudwatch_log_metric_filter" "secret_access" {
  name           = "secret-access-monitoring"
  log_group_name = aws_cloudwatch_log_group.audit.name
  pattern        = "[time, request_id, event_type=SecretManager*, ...]"
  
  metric_transformation {
    name      = "SecretAccess"
    namespace = "CryptoTrading/Security"
    value     = "1"
  }
}

# Outputs
output "vault_endpoint" {
  value = "https://vault.${var.domain_name}"
}

output "secrets_manager_endpoint" {
  value = "https://secretsmanager.${var.aws_region}.amazonaws.com"
}