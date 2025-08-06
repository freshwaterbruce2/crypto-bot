# Multi-Region Disaster Recovery Configuration
# Automated failover and backup systems for business continuity

# Secondary Region Provider
provider "aws" {
  alias  = "secondary"
  region = var.aws_secondary_region
  
  default_tags {
    tags = {
      Environment = "production-dr"
      Project     = "crypto-trading-bot"
      ManagedBy   = "terraform"
    }
  }
}

# Disaster Recovery VPC in Secondary Region
module "dr_networking" {
  source = "./modules/aws-networking"
  
  providers = {
    aws = aws.secondary
  }
  
  vpc_cidr = "10.1.0.0/16"
  
  availability_zones = [
    "${var.aws_secondary_region}a",
    "${var.aws_secondary_region}b",
    "${var.aws_secondary_region}c"
  ]
  
  private_subnet_cidrs = [
    "10.1.1.0/24",
    "10.1.2.0/24",
    "10.1.3.0/24"
  ]
  
  public_subnet_cidrs = [
    "10.1.101.0/24",
    "10.1.102.0/24",
    "10.1.103.0/24"
  ]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  
  tags = {
    Name        = "crypto-trading-dr-vpc"
    Environment = "production-dr"
  }
}

# VPC Peering between regions
resource "aws_vpc_peering_connection" "primary_to_dr" {
  vpc_id        = module.aws_networking.vpc_id
  peer_vpc_id   = module.dr_networking.vpc_id
  peer_region   = var.aws_secondary_region
  auto_accept   = false
  
  tags = {
    Name = "primary-to-dr-peering"
  }
}

# Accept peering in secondary region
resource "aws_vpc_peering_connection_accepter" "dr" {
  provider                  = aws.secondary
  vpc_peering_connection_id = aws_vpc_peering_connection.primary_to_dr.id
  auto_accept               = true
  
  tags = {
    Name = "dr-peering-accepter"
  }
}

# Route53 Health Checks
resource "aws_route53_health_check" "primary" {
  fqdn              = aws_lb.trading_api.dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = "3"
  request_interval  = "30"
  
  tags = {
    Name = "primary-region-health"
  }
}

resource "aws_route53_health_check" "secondary" {
  fqdn              = aws_lb.trading_api_dr.dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = "3"
  request_interval  = "30"
  
  tags = {
    Name = "secondary-region-health"
  }
}

# Route53 Failover Records
resource "aws_route53_record" "primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  
  alias {
    name                   = aws_lb.trading_api.dns_name
    zone_id                = aws_lb.trading_api.zone_id
    evaluate_target_health = true
  }
  
  set_identifier = "Primary"
  failover_routing_policy {
    type = "PRIMARY"
  }
  
  health_check_id = aws_route53_health_check.primary.id
}

resource "aws_route53_record" "secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  
  alias {
    name                   = aws_lb.trading_api_dr.dns_name
    zone_id                = aws_lb.trading_api_dr.zone_id
    evaluate_target_health = true
  }
  
  set_identifier = "Secondary"
  failover_routing_policy {
    type = "SECONDARY"
  }
  
  health_check_id = aws_route53_health_check.secondary.id
}

# S3 Cross-Region Replication for Backups
resource "aws_s3_bucket" "backups_primary" {
  bucket = "crypto-trading-backups-${var.aws_region}"
  
  tags = {
    Name        = "crypto-trading-backups-primary"
    Environment = "production"
  }
}

resource "aws_s3_bucket" "backups_dr" {
  provider = aws.secondary
  bucket   = "crypto-trading-backups-${var.aws_secondary_region}"
  
  tags = {
    Name        = "crypto-trading-backups-dr"
    Environment = "production-dr"
  }
}

resource "aws_s3_bucket_replication_configuration" "backup_replication" {
  role   = aws_iam_role.replication.arn
  bucket = aws_s3_bucket.backups_primary.id
  
  rule {
    id     = "replicate-all"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.backups_dr.arn
      storage_class = "STANDARD_IA"
      
      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
      
      metrics {
        status = "Enabled"
        event_threshold {
          minutes = 15
        }
      }
    }
  }
}

# EKS Cluster in DR Region
resource "aws_eks_cluster" "dr" {
  provider = aws.secondary
  
  name     = "crypto-trading-dr"
  role_arn = aws_iam_role.eks_cluster_dr.arn
  version  = "1.28"
  
  vpc_config {
    subnet_ids              = module.dr_networking.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = [aws_security_group.eks_cluster_dr.id]
  }
  
  encryption_config {
    provider {
      key_arn = aws_kms_key.eks_dr.arn
    }
    resources = ["secrets"]
  }
  
  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator"
  ]
}

# DR Node Group
resource "aws_eks_node_group" "dr_standby" {
  provider = aws.secondary
  
  cluster_name    = aws_eks_cluster.dr.name
  node_group_name = "dr-standby"
  node_role_arn   = aws_iam_role.eks_nodes_dr.arn
  subnet_ids      = module.dr_networking.private_subnet_ids
  
  scaling_config {
    desired_size = 1
    max_size     = 10
    min_size     = 1
  }
  
  instance_types = ["m5.large"]
  
  labels = {
    "node.kubernetes.io/purpose" = "dr-standby"
  }
}

# Velero for Kubernetes Backup
resource "helm_release" "velero" {
  name       = "velero"
  repository = "https://vmware-tanzu.github.io/helm-charts"
  chart      = "velero"
  version    = "5.1.0"
  namespace  = "velero"
  
  create_namespace = true
  
  values = [
    <<-EOT
    configuration:
      provider: aws
      backupStorageLocation:
        bucket: ${aws_s3_bucket.velero_backups.bucket}
        config:
          region: ${var.aws_region}
      volumeSnapshotLocation:
        config:
          region: ${var.aws_region}
    
    initContainers:
      - name: velero-plugin-for-aws
        image: velero/velero-plugin-for-aws:v1.8.0
        volumeMounts:
          - mountPath: /target
            name: plugins
    
    schedules:
      daily-backup:
        disabled: false
        schedule: "0 2 * * *"
        template:
          ttl: "720h0m0s"
          includedNamespaces:
            - trading-system
          storageLocation: default
    EOT
  ]
}

# Automated Failover Lambda
resource "aws_lambda_function" "failover_orchestrator" {
  filename         = "lambda-failover.zip"
  function_name    = "crypto-trading-failover"
  role            = aws_iam_role.lambda_failover.arn
  handler         = "failover.handler"
  source_code_hash = filebase64sha256("lambda-failover.zip")
  runtime         = "python3.11"
  timeout         = 300
  
  environment {
    variables = {
      PRIMARY_REGION     = var.aws_region
      SECONDARY_REGION   = var.aws_secondary_region
      PRIMARY_CLUSTER    = aws_eks_cluster.production.name
      SECONDARY_CLUSTER  = aws_eks_cluster.dr.name
      SNS_TOPIC         = aws_sns_topic.failover_alerts.arn
    }
  }
  
  vpc_config {
    subnet_ids         = module.aws_networking.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }
}

# CloudWatch Event Rule for Automated Failover
resource "aws_cloudwatch_event_rule" "health_check_failure" {
  name        = "crypto-trading-health-failure"
  description = "Trigger failover on health check failures"
  
  event_pattern = jsonencode({
    source      = ["aws.route53"]
    detail-type = ["Route 53 Health Check State Change"]
    detail = {
      state = ["ALARM"]
    }
  })
}

resource "aws_cloudwatch_event_target" "failover" {
  rule      = aws_cloudwatch_event_rule.health_check_failure.name
  target_id = "FailoverLambda"
  arn       = aws_lambda_function.failover_orchestrator.arn
}

# Backup Vault with Lock
resource "aws_backup_vault" "trading" {
  name        = "crypto-trading-vault"
  kms_key_arn = aws_kms_key.backup.arn
  
  tags = {
    Name = "crypto-trading-backup-vault"
  }
}

resource "aws_backup_vault_lock_configuration" "trading" {
  backup_vault_name   = aws_backup_vault.trading.name
  min_retention_days  = 7
  max_retention_days  = 365
  
  changeable_for_days = 3
}

# Disaster Recovery Testing Schedule
resource "aws_cloudwatch_event_rule" "dr_test" {
  name                = "crypto-trading-dr-test"
  description         = "Monthly DR testing"
  schedule_expression = "cron(0 10 1 * ? *)"  # First day of month at 10 AM
}

resource "aws_lambda_function" "dr_test" {
  filename         = "lambda-dr-test.zip"
  function_name    = "crypto-trading-dr-test"
  role            = aws_iam_role.lambda_dr_test.arn
  handler         = "dr_test.handler"
  source_code_hash = filebase64sha256("lambda-dr-test.zip")
  runtime         = "python3.11"
  timeout         = 900
  
  environment {
    variables = {
      DR_REGION        = var.aws_secondary_region
      DR_CLUSTER       = aws_eks_cluster.dr.name
      TEST_NAMESPACE   = "dr-test"
      NOTIFICATION_SNS = aws_sns_topic.dr_test_results.arn
    }
  }
}

# DR Dashboard
resource "aws_cloudwatch_dashboard" "disaster_recovery" {
  dashboard_name = "crypto-trading-dr"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Route53", "HealthCheckStatus", "HealthCheckId", aws_route53_health_check.primary.id, { label = "Primary Region" }],
            ["...", aws_route53_health_check.secondary.id, { label = "Secondary Region" }]
          ]
          period = 60
          stat   = "Average"
          region = "us-east-1"
          title  = "Region Health Status"
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "ReplicationLatency", "SourceBucket", aws_s3_bucket.backups_primary.id]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Backup Replication Latency"
        }
      }
    ]
  })
}

# RTO/RPO Monitoring
resource "aws_cloudwatch_metric_alarm" "rto_breach" {
  alarm_name          = "crypto-trading-rto-breach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FailoverTime"
  namespace           = "CryptoTrading/DR"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "300"  # 5 minute RTO
  alarm_description   = "RTO exceeded threshold"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
}

# Outputs
output "dr_cluster_endpoint" {
  value = aws_eks_cluster.dr.endpoint
}

output "failover_status_dashboard" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.disaster_recovery.dashboard_name}"
}

output "backup_vault_arn" {
  value = aws_backup_vault.trading.arn
}