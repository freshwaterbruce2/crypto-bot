# Production Cloud Deployment Configuration
# Multi-cloud setup for high availability crypto trading platform

terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
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
    bucket         = "crypto-trading-bot-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = "production"
      Project     = "crypto-trading-bot"
      ManagedBy   = "terraform"
      Compliance  = "financial-services"
    }
  }
}

# GCP Provider Configuration
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Multi-Region VPC Configuration (AWS)
module "aws_networking" {
  source = "./modules/aws-networking"
  
  vpc_cidr = "10.0.0.0/16"
  
  availability_zones = [
    "${var.aws_region}a",
    "${var.aws_region}b",
    "${var.aws_region}c"
  ]
  
  private_subnet_cidrs = [
    "10.0.1.0/24",
    "10.0.2.0/24",
    "10.0.3.0/24"
  ]
  
  public_subnet_cidrs = [
    "10.0.101.0/24",
    "10.0.102.0/24",
    "10.0.103.0/24"
  ]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  enable_flow_logs   = true
  
  tags = {
    Name        = "crypto-trading-production-vpc"
    Environment = "production"
  }
}

# EKS Cluster Configuration
resource "aws_eks_cluster" "production" {
  name     = "crypto-trading-production"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.28"
  
  vpc_config {
    subnet_ids              = module.aws_networking.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }
  
  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }
  
  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# EKS Node Groups with Auto-Scaling
resource "aws_eks_node_group" "trading_engines" {
  cluster_name    = aws_eks_cluster.production.name
  node_group_name = "trading-engines"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = module.aws_networking.private_subnet_ids
  
  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 3
  }
  
  update_config {
    max_unavailable_percentage = 33
  }
  
  instance_types = ["m5.xlarge", "m5a.xlarge"]
  
  disk_size = 100
  
  launch_template {
    id      = aws_launch_template.trading_nodes.id
    version = "$Latest"
  }
  
  labels = {
    "node.kubernetes.io/purpose" = "trading"
    "node.kubernetes.io/lifecycle" = "spot"
  }
  
  taints {
    key    = "trading"
    value  = "true"
    effect = "NO_SCHEDULE"
  }
}

# Launch Template for Trading Nodes
resource "aws_launch_template" "trading_nodes" {
  name_prefix = "trading-node-"
  
  block_device_mappings {
    device_name = "/dev/xvda"
    
    ebs {
      volume_size           = 100
      volume_type           = "gp3"
      iops                  = 3000
      throughput            = 125
      encrypted             = true
      kms_key_id           = aws_kms_key.ebs.arn
      delete_on_termination = true
    }
  }
  
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  
  monitoring {
    enabled = true
  }
  
  network_interfaces {
    associate_public_ip_address = false
    delete_on_termination       = true
    security_groups            = [aws_security_group.trading_nodes.id]
  }
  
  user_data = base64encode(templatefile("${path.module}/scripts/node-init.sh", {
    cluster_name = aws_eks_cluster.production.name
    region       = var.aws_region
  }))
}

# Auto-Scaling Configuration
resource "aws_autoscaling_policy" "trading_scale_up" {
  name                   = "trading-scale-up"
  scaling_adjustment     = 2
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_eks_node_group.trading_engines.resources[0].autoscaling_groups[0].name
}

resource "aws_autoscaling_policy" "trading_scale_down" {
  name                   = "trading-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 600
  autoscaling_group_name = aws_eks_node_group.trading_engines.resources[0].autoscaling_groups[0].name
}

# CloudWatch Metrics for Auto-Scaling
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "trading-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.trading_scale_up.arn]
  
  dimensions = {
    AutoScalingGroupName = aws_eks_node_group.trading_engines.resources[0].autoscaling_groups[0].name
  }
}

resource "aws_cloudwatch_metric_alarm" "low_cpu" {
  alarm_name          = "trading-low-cpu"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "This metric monitors cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.trading_scale_down.arn]
  
  dimensions = {
    AutoScalingGroupName = aws_eks_node_group.trading_engines.resources[0].autoscaling_groups[0].name
  }
}

# GKE Cluster Configuration (GCP)
resource "google_container_cluster" "production" {
  name     = "crypto-trading-production"
  location = var.gcp_region
  
  # Regional cluster for high availability
  node_locations = [
    "${var.gcp_region}-a",
    "${var.gcp_region}-b",
    "${var.gcp_region}-c"
  ]
  
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.private.name
  
  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Workload Identity for secure pod access
  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block = "172.16.0.0/28"
  }
  
  # Security configuration
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  # Binary Authorization for container security
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
  
  # Network policy
  network_policy {
    enabled = true
  }
  
  # Pod security policy
  pod_security_policy_config {
    enabled = true
  }
  
  # Addons
  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    http_load_balancing {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }
  
  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
}

# GKE Node Pool with Auto-scaling
resource "google_container_node_pool" "trading_pool" {
  name       = "trading-pool"
  location   = var.gcp_region
  cluster    = google_container_cluster.production.name
  
  # Auto-scaling configuration
  autoscaling {
    min_node_count = 3
    max_node_count = 10
  }
  
  # Node configuration
  node_config {
    preemptible  = false
    machine_type = "n2-standard-4"
    
    # Disk configuration
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    
    # Security
    service_account = google_service_account.gke_nodes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Labels
    labels = {
      environment = "production"
      purpose     = "trading"
    }
    
    # Taints
    taint {
      key    = "trading"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
    
    # Workload metadata
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Shielded instance
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
  
  # Management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Global Load Balancer (AWS)
resource "aws_lb" "trading_api" {
  name               = "crypto-trading-api"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.aws_networking.public_subnet_ids
  
  enable_deletion_protection = true
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    enabled = true
  }
  
  tags = {
    Name = "crypto-trading-api-lb"
  }
}

# CloudFront Distribution for Global Edge
resource "aws_cloudfront_distribution" "trading_api" {
  enabled             = true
  is_ipv6_enabled    = true
  comment            = "Crypto Trading API Global Distribution"
  default_root_object = "health"
  
  origin {
    domain_name = aws_lb.trading_api.dns_name
    origin_id   = "ALB-${aws_lb.trading_api.id}"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB-${aws_lb.trading_api.id}"
    
    forwarded_values {
      query_string = true
      headers      = ["*"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }
  
  price_class = "PriceClass_All"
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.trading_api.arn
    ssl_support_method  = "sni-only"
  }
  
  web_acl_id = aws_wafv2_web_acl.trading_api.arn
}

# Output important values
output "eks_cluster_endpoint" {
  value = aws_eks_cluster.production.endpoint
}

output "gke_cluster_endpoint" {
  value = google_container_cluster.production.endpoint
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.trading_api.domain_name
}

output "load_balancer_dns" {
  value = aws_lb.trading_api.dns_name
}