# Production Deployment Variables
# Configure these values for your specific deployment

variable "aws_region" {
  description = "Primary AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_secondary_region" {
  description = "Secondary AWS region for disaster recovery"
  type        = string
  default     = "us-west-2"
}

variable "gcp_project_id" {
  description = "GCP project ID for multi-cloud deployment"
  type        = string
}

variable "gcp_region" {
  description = "Primary GCP region for deployment"
  type        = string
  default     = "us-central1"
}

variable "domain_name" {
  description = "Primary domain name for the trading platform"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\\.[a-z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid format."
  }
}

variable "cert_admin_email" {
  description = "Email address for SSL certificate notifications"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.cert_admin_email))
    error_message = "Must be a valid email address."
  }
}

# API Credentials (stored securely, never in code)
variable "kraken_api_key" {
  description = "Kraken API key (read/trade only, no withdrawal)"
  type        = string
  sensitive   = true
}

variable "kraken_api_secret" {
  description = "Kraken API secret"
  type        = string
  sensitive   = true
}

# Database Configuration
variable "source_db_host" {
  description = "Source database host for migration"
  type        = string
  default     = ""
}

variable "source_db_port" {
  description = "Source database port"
  type        = number
  default     = 5432
}

variable "source_db_username" {
  description = "Source database username"
  type        = string
  default     = "postgres"
}

variable "source_db_password" {
  description = "Source database password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "source_db_name" {
  description = "Source database name"
  type        = string
  default     = "trading_bot"
}

# Trading Configuration
variable "trading_pairs" {
  description = "List of trading pairs to enable"
  type        = list(string)
  default = [
    "SHIB/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "ALGO/USDT",
    "MATIC/USDT",
    "XRP/USDT"
  ]
}

variable "position_size_usdt" {
  description = "Default position size in USDT"
  type        = number
  default     = 100
  validation {
    condition     = var.position_size_usdt >= 10 && var.position_size_usdt <= 10000
    error_message = "Position size must be between 10 and 10000 USDT."
  }
}

variable "max_positions" {
  description = "Maximum number of concurrent positions"
  type        = number
  default     = 10
  validation {
    condition     = var.max_positions >= 1 && var.max_positions <= 50
    error_message = "Max positions must be between 1 and 50."
  }
}

variable "risk_percentage" {
  description = "Risk percentage per trade"
  type        = number
  default     = 0.02
  validation {
    condition     = var.risk_percentage > 0 && var.risk_percentage <= 0.05
    error_message = "Risk percentage must be between 0 and 5%."
  }
}

# Compliance Configuration
variable "compliance_email_list" {
  description = "Comma-separated list of emails for compliance reports"
  type        = string
}

variable "compliance_alert_email" {
  description = "Email for critical compliance alerts"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  sensitive   = true
  default     = ""
}

# GitHub Configuration
variable "github_repo_name" {
  description = "GitHub repository name for the project"
  type        = string
  default     = "crypto-trading-bot-2025"
}

# Resource Naming
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "crypto-trading"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# Kubernetes Configuration
variable "k8s_namespace" {
  description = "Primary Kubernetes namespace for the application"
  type        = string
  default     = "trading-system"
}

# Cost Management
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "reserved_instance_term" {
  description = "Reserved instance term in years"
  type        = number
  default     = 1
  validation {
    condition     = contains([1, 3], var.reserved_instance_term)
    error_message = "Reserved instance term must be 1 or 3 years."
  }
}

# Monitoring Configuration
variable "datadog_api_key" {
  description = "DataDog API key for monitoring"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key for alerts"
  type        = string
  sensitive   = true
  default     = ""
}

# Feature Flags
variable "enable_paper_trading" {
  description = "Enable paper trading mode"
  type        = bool
  default     = false
}

variable "enable_advanced_analytics" {
  description = "Enable advanced analytics features"
  type        = bool
  default     = true
}

variable "enable_multi_exchange" {
  description = "Enable multi-exchange support"
  type        = bool
  default     = false
}

# Network Configuration
variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges for admin access"
  type        = list(string)
  default     = []
  validation {
    condition = alltrue([
      for ip in var.allowed_ip_ranges : can(cidrhost(ip, 0))
    ])
    error_message = "All IP ranges must be valid CIDR blocks."
  }
}

# Tags
variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "CryptoTradingBot"
    ManagedBy   = "Terraform"
    Environment = "Production"
    CostCenter  = "Trading"
    Compliance  = "PCI-DSS,SOC2"
  }
}

# Locals for computed values
locals {
  full_domain = "${var.environment}.${var.domain_name}"
  
  common_labels = {
    "app.kubernetes.io/name"       = var.project_name
    "app.kubernetes.io/instance"   = var.environment
    "app.kubernetes.io/managed-by" = "terraform"
  }
  
  db_connection_string = "postgresql://${aws_rds_cluster.primary.master_username}:${random_password.db_password.result}@${aws_rds_cluster.primary.endpoint}:5432/${aws_rds_cluster.primary.database_name}"
}

# Random password generation
resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_password" "redis_auth" {
  length  = 32
  special = false  # Redis doesn't like special characters in auth tokens
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}