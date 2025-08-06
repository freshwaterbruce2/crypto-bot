# Compliance Monitoring and Reporting Configuration
# Real-time compliance checking for financial regulations

# AWS Config for continuous compliance monitoring
resource "aws_config_configuration_recorder" "trading" {
  name     = "crypto-trading-recorder"
  role_arn = aws_iam_role.config.arn
  
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "trading" {
  name           = "crypto-trading-delivery"
  s3_bucket_name = aws_s3_bucket.config.bucket
  
  snapshot_delivery_properties {
    delivery_frequency = "TwentyFour_Hours"
  }
}

resource "aws_config_configuration_recorder_status" "trading" {
  name       = aws_config_configuration_recorder.trading.name
  is_enabled = true
  
  depends_on = [aws_config_delivery_channel.trading]
}

# Config Rules for Financial Compliance
resource "aws_config_config_rule" "encryption_at_rest" {
  name = "crypto-trading-encryption-at-rest"
  
  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }
  
  depends_on = [aws_config_configuration_recorder.trading]
}

resource "aws_config_config_rule" "encryption_in_transit" {
  name = "crypto-trading-encryption-in-transit"
  
  source {
    owner             = "AWS"
    source_identifier = "ELB_TLS_HTTPS_LISTENERS_ONLY"
  }
}

resource "aws_config_config_rule" "access_logging" {
  name = "crypto-trading-access-logging"
  
  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_LOGGING_ENABLED"
  }
}

resource "aws_config_config_rule" "mfa_enabled" {
  name = "crypto-trading-mfa-enabled"
  
  source {
    owner             = "AWS"
    source_identifier = "MFA_ENABLED_FOR_IAM_CONSOLE_ACCESS"
  }
}

# Custom Lambda for Trading-Specific Compliance
resource "aws_lambda_function" "compliance_checker" {
  filename         = "lambda-compliance.zip"
  function_name    = "crypto-trading-compliance"
  role            = aws_iam_role.lambda_compliance.arn
  handler         = "compliance.handler"
  source_code_hash = filebase64sha256("lambda-compliance.zip")
  runtime         = "python3.11"
  timeout         = 300
  
  environment {
    variables = {
      COMPLIANCE_TABLE = aws_dynamodb_table.compliance_results.name
      SNS_TOPIC       = aws_sns_topic.compliance_alerts.arn
      REGULATIONS     = jsonencode({
        "PCI_DSS"     = true
        "SOC2"        = true
        "ISO_27001"   = true
        "GDPR"        = true
        "MiFID_II"    = true
        "AML_KYC"     = true
      })
    }
  }
}

# EventBridge Rule for Continuous Compliance Checks
resource "aws_cloudwatch_event_rule" "compliance_schedule" {
  name                = "crypto-trading-compliance"
  description         = "Hourly compliance verification"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "compliance" {
  rule      = aws_cloudwatch_event_rule.compliance_schedule.name
  target_id = "ComplianceLambda"
  arn       = aws_lambda_function.compliance_checker.arn
}

# GuardDuty for Threat Detection
resource "aws_guardduty_detector" "trading" {
  enable = true
  
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
  }
}

# Security Hub for Centralized Compliance
resource "aws_securityhub_account" "trading" {}

resource "aws_securityhub_standards_subscription" "pci_dss" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/pci-dss/v/3.2.1"
  depends_on    = [aws_securityhub_account.trading]
}

resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/aws-foundational-security-best-practices/v/1.0.0"
  depends_on    = [aws_securityhub_account.trading]
}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/cis-aws-foundations-benchmark/v/1.4.0"
  depends_on    = [aws_securityhub_account.trading]
}

# CloudTrail for Audit Logging
resource "aws_cloudtrail" "trading" {
  name                          = "crypto-trading-audit"
  s3_bucket_name               = aws_s3_bucket.cloudtrail.bucket
  include_global_service_events = true
  is_multi_region_trail        = true
  enable_logging               = true
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::*/*"]
    }
    
    data_resource {
      type   = "AWS::RDS::DBCluster"
      values = ["arn:aws:rds:*:*:cluster:*"]
    }
  }
  
  insight_selector {
    insight_type = "ApiCallRateInsight"
  }
  
  depends_on = [aws_s3_bucket_policy.cloudtrail]
}

# DynamoDB Table for Compliance Results
resource "aws_dynamodb_table" "compliance_results" {
  name         = "crypto-trading-compliance"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "check_id"
  range_key    = "timestamp"
  
  attribute {
    name = "check_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "N"
  }
  
  attribute {
    name = "regulation"
    type = "S"
  }
  
  global_secondary_index {
    name            = "regulation-index"
    hash_key        = "regulation"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  point_in_time_recovery {
    enabled = true
  }
  
  server_side_encryption {
    enabled = true
  }
  
  tags = {
    Name = "crypto-trading-compliance"
  }
}

# Real-time Compliance Dashboard
resource "aws_cloudwatch_dashboard" "compliance" {
  dashboard_name = "crypto-trading-compliance"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["CryptoTrading/Compliance", "ChecksPassed", { stat = "Sum", color = "#2ca02c" }],
            [".", "ChecksFailed", { stat = "Sum", color = "#d62728" }]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "Compliance Check Results"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CryptoTrading/Compliance", "PCIDSSCompliance", { stat = "Average" }],
            [".", "SOC2Compliance", { stat = "Average" }],
            [".", "ISO27001Compliance", { stat = "Average" }],
            [".", "GDPRCompliance", { stat = "Average" }],
            [".", "MiFIDIICompliance", { stat = "Average" }],
            [".", "AMLKYCCompliance", { stat = "Average" }]
          ]
          period = 3600
          stat   = "Average"
          region = var.aws_region
          title  = "Regulation Compliance Scores"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type   = "log"
        width  = 12
        height = 6
        properties = {
          query   = "SOURCE '/aws/lambda/crypto-trading-compliance' | fields @timestamp, regulation, status, details | filter status = 'FAILED' | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Compliance Failures"
        }
      }
    ]
  })
}

# Falco for Runtime Security
resource "helm_release" "falco" {
  name       = "falco"
  repository = "https://falcosecurity.github.io/charts"
  chart      = "falco"
  version    = "3.8.0"
  namespace  = "falco"
  
  create_namespace = true
  
  values = [
    <<-EOT
    falco:
      grpc:
        enabled: true
      grpcOutput:
        enabled: true
      
      rules_file:
        - /etc/falco/falco_rules.yaml
        - /etc/falco/falco_rules.local.yaml
        - /etc/falco/rules.d
        - /etc/falco/crypto_trading_rules.yaml
      
      customRules:
        crypto_trading_rules.yaml: |
          - rule: Unauthorized API Access
            desc: Detect unauthorized access to trading APIs
            condition: >
              spawned_process and proc.name in (curl, wget, python, node) and
              (proc.args contains "api.kraken.com" or proc.args contains "trade" or proc.args contains "order")
            output: >
              Potential unauthorized API access (user=%user.name command=%proc.cmdline)
            priority: WARNING
            
          - rule: Suspicious Database Query
            desc: Detect potentially malicious database queries
            condition: >
              spawned_process and proc.name in (psql, mysql) and
              (proc.args contains "DELETE" or proc.args contains "DROP" or proc.args contains "TRUNCATE")
            output: >
              Suspicious database operation detected (user=%user.name command=%proc.cmdline)
            priority: CRITICAL
            
          - rule: Configuration File Modified
            desc: Detect modifications to critical configuration files
            condition: >
              open_write and 
              (fd.name endswith ".env" or fd.name endswith "config.json" or fd.name contains "/etc/")
            output: >
              Critical configuration file modified (user=%user.name file=%fd.name)
            priority: ERROR
    EOT
  ]
}

# Open Policy Agent for Policy Enforcement
resource "helm_release" "opa" {
  name       = "opa"
  repository = "https://open-policy-agent.github.io/kube-mgmt/charts"
  chart      = "opa-kube-mgmt"
  version    = "7.1.0"
  namespace  = "opa"
  
  create_namespace = true
  
  values = [
    <<-EOT
    opa:
      replicas: 3
      
    mgmt:
      replicas: 1
      configmapPolicies:
        enabled: true
        namespaces: [trading-system, default]
    EOT
  ]
}

# Compliance Policies ConfigMap
resource "kubernetes_config_map" "compliance_policies" {
  metadata {
    name      = "compliance-policies"
    namespace = "opa"
  }
  
  data = {
    "trading_compliance.rego" = <<-EOT
      package trading.compliance
      
      # Enforce encryption for all API communications
      deny[msg] {
        input.request.kind.kind == "Service"
        input.request.object.spec.type == "LoadBalancer"
        not input.request.object.metadata.annotations["service.beta.kubernetes.io/aws-load-balancer-ssl-cert"]
        msg := "All LoadBalancer services must use SSL/TLS"
      }
      
      # Enforce resource limits
      deny[msg] {
        input.request.kind.kind == "Deployment"
        container := input.request.object.spec.template.spec.containers[_]
        not container.resources.limits.memory
        msg := sprintf("Container %v must have memory limits", [container.name])
      }
      
      # Enforce security context
      deny[msg] {
        input.request.kind.kind == "Deployment"
        not input.request.object.spec.template.spec.securityContext.runAsNonRoot
        msg := "Deployments must run as non-root user"
      }
      
      # Enforce network policies
      deny[msg] {
        input.request.kind.kind == "Namespace"
        not input.request.object.metadata.labels["network-policy-enforced"]
        msg := "All namespaces must have network policies enforced"
      }
    EOT
  }
}

# Automated Compliance Reporting
resource "aws_lambda_function" "compliance_reporter" {
  filename         = "lambda-compliance-report.zip"
  function_name    = "crypto-trading-compliance-report"
  role            = aws_iam_role.lambda_reporter.arn
  handler         = "reporter.handler"
  source_code_hash = filebase64sha256("lambda-compliance-report.zip")
  runtime         = "python3.11"
  timeout         = 900
  
  environment {
    variables = {
      COMPLIANCE_BUCKET = aws_s3_bucket.compliance_reports.bucket
      EMAIL_LIST       = var.compliance_email_list
      DASHBOARD_URL    = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.compliance.dashboard_name}"
    }
  }
}

# Weekly Compliance Report Schedule
resource "aws_cloudwatch_event_rule" "weekly_report" {
  name                = "crypto-trading-weekly-compliance"
  description         = "Generate weekly compliance report"
  schedule_expression = "cron(0 9 ? * MON *)"  # Every Monday at 9 AM
}

resource "aws_cloudwatch_event_target" "weekly_report" {
  rule      = aws_cloudwatch_event_rule.weekly_report.name
  target_id = "ComplianceReporter"
  arn       = aws_lambda_function.compliance_reporter.arn
}

# Compliance Alerts
resource "aws_sns_topic" "compliance_alerts" {
  name = "crypto-trading-compliance-alerts"
  
  kms_master_key_id = aws_kms_key.sns.id
}

resource "aws_sns_topic_subscription" "compliance_email" {
  topic_arn = aws_sns_topic.compliance_alerts.arn
  protocol  = "email"
  endpoint  = var.compliance_alert_email
}

resource "aws_sns_topic_subscription" "compliance_slack" {
  topic_arn = aws_sns_topic.compliance_alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# Outputs
output "compliance_dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.compliance.dashboard_name}"
}

output "security_hub_url" {
  value = "https://console.aws.amazon.com/securityhub/home?region=${var.aws_region}#/summary"
}

output "compliance_report_bucket" {
  value = aws_s3_bucket.compliance_reports.bucket
}