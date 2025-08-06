# Terraform Configuration for Crypto Trading Platform
# Multi-region deployment with auto-scaling and high availability

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket         = "crypto-trading-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

# Primary AWS Provider (US East)
provider "aws" {
  region = var.primary_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "crypto-trading-platform"
      ManagedBy   = "terraform"
      Compliance  = "SOC2-FINRA"
    }
  }
}

# Secondary AWS Provider (EU West - DR Region)
provider "aws" {
  alias  = "dr"
  region = var.dr_region
  
  default_tags {
    tags = {
      Environment = "${var.environment}-dr"
      Project     = "crypto-trading-platform"
      ManagedBy   = "terraform"
      Compliance  = "SOC2-FINRA"
    }
  }
}

# VPC Configuration for Primary Region
module "vpc_primary" {
  source = "./modules/vpc"
  
  region               = var.primary_region
  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  enable_flow_logs   = true
  
  tags = {
    Name = "crypto-trading-vpc-primary"
    Type = "production"
  }
}

# VPC Configuration for DR Region
module "vpc_dr" {
  source = "./modules/vpc"
  providers = {
    aws = aws.dr
  }
  
  region               = var.dr_region
  vpc_cidr             = "10.1.0.0/16"
  availability_zones   = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
  private_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  public_subnet_cidrs  = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  enable_flow_logs   = true
  
  tags = {
    Name = "crypto-trading-vpc-dr"
    Type = "disaster-recovery"
  }
}

# EKS Cluster for Primary Region
module "eks_primary" {
  source = "./modules/eks"
  
  cluster_name     = "crypto-trading-prod"
  cluster_version  = "1.28"
  vpc_id           = module.vpc_primary.vpc_id
  subnet_ids       = module.vpc_primary.private_subnet_ids
  
  node_groups = {
    trading = {
      instance_types = ["c5.2xlarge", "c5.4xlarge"]
      min_size       = 3
      max_size       = 20
      desired_size   = 5
      
      labels = {
        workload = "trading"
        tier     = "critical"
      }
      
      taints = [{
        key    = "dedicated"
        value  = "trading"
        effect = "NO_SCHEDULE"
      }]
    }
    
    monitoring = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 5
      desired_size   = 3
      
      labels = {
        workload = "monitoring"
        tier     = "standard"
      }
    }
  }
  
  enable_irsa = true
  
  cluster_addons = {
    coredns = {
      addon_version = "v1.10.1-eksbuild.4"
    }
    kube-proxy = {
      addon_version = "v1.28.1-eksbuild.1"
    }
    vpc-cni = {
      addon_version = "v1.14.1-eksbuild.1"
    }
    aws-ebs-csi-driver = {
      addon_version = "v1.23.1-eksbuild.1"
    }
  }
}

# RDS Aurora Global Database
module "aurora_global" {
  source = "./modules/aurora"
  
  global_cluster_identifier = "crypto-trading-global"
  engine                    = "aurora-postgresql"
  engine_version            = "15.4"
  
  primary_cluster = {
    region                  = var.primary_region
    vpc_id                  = module.vpc_primary.vpc_id
    subnet_ids              = module.vpc_primary.private_subnet_ids
    instance_class          = "db.r6g.2xlarge"
    instances               = 3
    backup_retention_period = 30
    enable_backtrack        = true
  }
  
  secondary_clusters = [{
    region     = var.dr_region
    vpc_id     = module.vpc_dr.vpc_id
    subnet_ids = module.vpc_dr.private_subnet_ids
    instances  = 2
  }]
  
  enable_global_write_forwarding = true
  enable_iam_database_auth      = true
  
  performance_insights = {
    enabled          = true
    retention_period = 731 # 2 years
  }
}

# ElastiCache Redis Global Datastore
module "redis_global" {
  source = "./modules/elasticache"
  
  replication_group_id = "crypto-trading-cache"
  node_type            = "cache.r6g.xlarge"
  num_cache_clusters   = 3
  
  subnet_group_name = module.vpc_primary.elasticache_subnet_group_name
  security_group_ids = [module.security_groups.redis_sg_id]
  
  global_datastore = {
    enabled                    = true
    secondary_region           = var.dr_region
    secondary_subnet_group     = module.vpc_dr.elasticache_subnet_group_name
    secondary_security_groups  = [module.security_groups_dr.redis_sg_id]
  }
  
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  auth_token_enabled         = true
  
  parameter_group_family = "redis7"
  
  parameters = [
    {
      name  = "maxmemory-policy"
      value = "allkeys-lru"
    },
    {
      name  = "timeout"
      value = "300"
    }
  ]
}

# Application Load Balancer with WAF
module "alb" {
  source = "./modules/alb"
  
  name               = "crypto-trading-alb"
  vpc_id             = module.vpc_primary.vpc_id
  subnet_ids         = module.vpc_primary.public_subnet_ids
  security_group_ids = [module.security_groups.alb_sg_id]
  
  enable_deletion_protection = true
  enable_http2               = true
  enable_waf                 = true
  
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  
  certificate_arn = module.acm.certificate_arn
  
  target_groups = [
    {
      name             = "trading-api"
      port             = 8080
      protocol         = "HTTP"
      target_type      = "ip"
      health_check_path = "/health"
      health_check_interval = 10
      health_check_timeout = 5
      healthy_threshold = 2
      unhealthy_threshold = 3
    }
  ]
  
  waf_rules = [
    {
      name     = "RateLimitRule"
      priority = 1
      action   = "block"
      
      rate_based_statement = {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    },
    {
      name     = "GeoBlockRule"
      priority = 2
      action   = "block"
      
      geo_match_statement = {
        country_codes = var.blocked_countries
      }
    }
  ]
}

# Secrets Manager for API Keys and Credentials
module "secrets_manager" {
  source = "./modules/secrets"
  
  secrets = {
    kraken_api = {
      description = "Kraken Exchange API Credentials"
      rotation_enabled = true
      rotation_days = 30
      
      replica_regions = [var.dr_region]
    }
    
    database_credentials = {
      description = "RDS Aurora Master Credentials"
      rotation_enabled = true
      rotation_days = 90
      
      rotation_lambda_arn = module.rotation_lambda.arn
    }
    
    jwt_signing_key = {
      description = "JWT Token Signing Key"
      rotation_enabled = true
      rotation_days = 7
    }
  }
  
  kms_key_id = module.kms.key_id
}

# KMS for Encryption
module "kms" {
  source = "./modules/kms"
  
  alias_name        = "crypto-trading-master"
  description       = "Master key for crypto trading platform encryption"
  multi_region      = true
  
  key_policy = {
    enable_iam_user_permissions = true
    enable_key_rotation         = true
    
    key_administrators = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CryptoTradingAdmin"
    ]
    
    key_users = [
      module.eks_primary.cluster_iam_role_arn,
      module.aurora_global.cluster_iam_role_arn
    ]
  }
  
  replica_regions = [var.dr_region]
}

# Route53 Health Checks and Failover
module "route53" {
  source = "./modules/route53"
  
  domain_name = var.domain_name
  
  primary_alb_dns_name = module.alb.dns_name
  primary_alb_zone_id  = module.alb.zone_id
  
  dr_alb_dns_name = module.alb_dr.dns_name
  dr_alb_zone_id  = module.alb_dr.zone_id
  
  health_check_config = {
    primary = {
      fqdn              = "api.${var.domain_name}"
      port              = 443
      type              = "HTTPS"
      resource_path     = "/health"
      failure_threshold = 3
      request_interval  = 10
    }
    
    dr = {
      fqdn              = "api-dr.${var.domain_name}"
      port              = 443
      type              = "HTTPS"
      resource_path     = "/health"
      failure_threshold = 3
      request_interval  = 10
    }
  }
  
  enable_failover = true
}

# CloudWatch Monitoring and Alarms
module "monitoring" {
  source = "./modules/monitoring"
  
  alarms = {
    high_api_latency = {
      metric_name = "TargetResponseTime"
      namespace   = "AWS/ApplicationELB"
      statistic   = "Average"
      period      = 60
      threshold   = 1000 # 1 second
      
      dimensions = {
        LoadBalancer = module.alb.arn_suffix
      }
    }
    
    database_cpu = {
      metric_name = "CPUUtilization"
      namespace   = "AWS/RDS"
      statistic   = "Average"
      period      = 300
      threshold   = 80
      
      dimensions = {
        DBClusterIdentifier = module.aurora_global.cluster_id
      }
    }
    
    trading_errors = {
      metric_name = "TradingErrors"
      namespace   = "CryptoTrading/Production"
      statistic   = "Sum"
      period      = 300
      threshold   = 10
    }
  }
  
  sns_topic_arns = [module.sns.critical_alerts_topic_arn]
  
  dashboard_name = "crypto-trading-production"
}

# Auto Scaling Configuration
module "autoscaling" {
  source = "./modules/autoscaling"
  
  cluster_name = module.eks_primary.cluster_name
  
  policies = {
    trading_scale_up = {
      scaling_adjustment = 2
      cooldown           = 60
      
      metric_trigger = {
        metric_name = "PendingOrders"
        namespace   = "CryptoTrading/Production"
        statistic   = "Average"
        threshold   = 100
        comparison  = "GreaterThanThreshold"
      }
    }
    
    trading_scale_down = {
      scaling_adjustment = -1
      cooldown           = 300
      
      metric_trigger = {
        metric_name = "PendingOrders"
        namespace   = "CryptoTrading/Production"
        statistic   = "Average"
        threshold   = 20
        comparison  = "LessThanThreshold"
      }
    }
  }
}

# Backup Configuration
module "backup" {
  source = "./modules/backup"
  
  backup_vault_name = "crypto-trading-vault"
  
  backup_plans = {
    critical_data = {
      rule_name         = "daily_backups"
      schedule          = "cron(0 5 ? * * *)"
      target_vault_name = "crypto-trading-vault"
      
      lifecycle = {
        cold_storage_after = 30
        delete_after       = 365
      }
      
      recovery_point_tags = {
        Compliance = "SOC2"
        DataClass  = "Critical"
      }
    }
  }
  
  backup_selections = [
    {
      name = "rds_backups"
      resources = [
        module.aurora_global.cluster_arn
      ]
    },
    {
      name = "ebs_backups"
      resources = [
        "arn:aws:ec2:*:*:volume/*"
      ]
      
      conditions = {
        string_equals = {
          "aws:ResourceTag/Backup" = "true"
        }
      }
    }
  ]
  
  enable_cross_region_backup = true
  destination_region         = var.dr_region
}

# Outputs
output "api_endpoint" {
  description = "Production API endpoint"
  value       = "https://api.${var.domain_name}"
}

output "monitoring_dashboard" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.primary_region}.console.aws.amazon.com/cloudwatch/home?region=${var.primary_region}#dashboards:name=${module.monitoring.dashboard_name}"
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks_primary.cluster_endpoint
  sensitive   = true
}

output "database_endpoint" {
  description = "Aurora database endpoint"
  value       = module.aurora_global.cluster_endpoint
  sensitive   = true
}