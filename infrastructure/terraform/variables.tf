# Terraform Variables for Crypto Trading Platform

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "primary_region" {
  description = "Primary AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "dr_region" {
  description = "Disaster recovery AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "domain_name" {
  description = "Primary domain name for the platform"
  type        = string
}

variable "blocked_countries" {
  description = "List of country codes to block via WAF"
  type        = list(string)
  default     = ["KP", "IR", "CU", "SY"]
}

variable "allowed_ip_ranges" {
  description = "Whitelisted IP ranges for admin access"
  type        = list(string)
  default     = []
}

variable "trading_pairs" {
  description = "Enabled trading pairs"
  type        = list(string)
  default = [
    "BTC/USD",
    "ETH/USD",
    "BTC/USDT",
    "ETH/USDT"
  ]
}

variable "enable_paper_trading" {
  description = "Enable paper trading mode"
  type        = bool
  default     = false
}

variable "max_position_size" {
  description = "Maximum position size in USD"
  type        = number
  default     = 100000
}

variable "max_daily_trades" {
  description = "Maximum number of trades per day"
  type        = number
  default     = 1000
}

variable "compliance_mode" {
  description = "Compliance mode (SOC2, FINRA, etc)"
  type        = string
  default     = "SOC2-FINRA"
}

variable "alert_email" {
  description = "Email for critical alerts"
  type        = string
  sensitive   = true
}

variable "alert_phone" {
  description = "Phone number for critical alerts (SMS)"
  type        = string
  sensitive   = true
}

variable "datadog_api_key" {
  description = "Datadog API key for external monitoring"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key for incident management"
  type        = string
  sensitive   = true
  default     = ""
}