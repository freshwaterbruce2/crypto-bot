# High-Availability Load Balancing Configuration
# Multi-tier load balancing for crypto trading traffic

# Global Accelerator for ultra-low latency
resource "aws_globalaccelerator_accelerator" "trading" {
  name            = "crypto-trading-global"
  ip_address_type = "IPV4"
  enabled         = true
  
  attributes {
    flow_logs_enabled   = true
    flow_logs_s3_bucket = aws_s3_bucket.flow_logs.bucket
    flow_logs_s3_prefix = "global-accelerator/"
  }
  
  tags = {
    Name        = "crypto-trading-accelerator"
    Environment = "production"
  }
}

# Listener for Global Accelerator
resource "aws_globalaccelerator_listener" "trading" {
  accelerator_arn = aws_globalaccelerator_accelerator.trading.id
  client_affinity = "SOURCE_IP"
  protocol        = "TCP"
  
  port_range {
    from_port = 443
    to_port   = 443
  }
  
  port_range {
    from_port = 80
    to_port   = 80
  }
}

# Endpoint groups for multi-region
resource "aws_globalaccelerator_endpoint_group" "primary" {
  listener_arn = aws_globalaccelerator_listener.trading.id
  
  endpoint_group_region = var.aws_region
  
  health_check_interval_seconds = 10
  health_check_path            = "/health"
  health_check_port            = 443
  health_check_protocol        = "HTTPS"
  threshold_count              = 3
  
  traffic_dial_percentage = 100
  
  endpoint_configuration {
    endpoint_id = aws_lb.trading_api.arn
    weight      = 100
  }
  
  port_override {
    listener_port = 443
    endpoint_port = 443
  }
}

# Application Load Balancer for HTTPS traffic
resource "aws_lb" "trading_api" {
  name               = "crypto-trading-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.aws_networking.public_subnet_ids
  
  enable_deletion_protection = true
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  idle_timeout              = 4000
  
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb"
    enabled = true
  }
  
  tags = {
    Name = "crypto-trading-api-alb"
  }
}

# Network Load Balancer for WebSocket traffic
resource "aws_lb" "trading_websocket" {
  name               = "crypto-trading-ws-nlb"
  internal           = false
  load_balancer_type = "network"
  subnets           = module.aws_networking.public_subnet_ids
  
  enable_deletion_protection = true
  enable_cross_zone_load_balancing = true
  
  tags = {
    Name = "crypto-trading-websocket-nlb"
  }
}

# Target Groups for ALB
resource "aws_lb_target_group" "api" {
  name     = "crypto-trading-api"
  port     = 443
  protocol = "HTTPS"
  vpc_id   = module.aws_networking.vpc_id
  
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTPS"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
  
  deregistration_delay = 30
  
  tags = {
    Name = "crypto-trading-api-tg"
  }
}

# Target Group for WebSocket
resource "aws_lb_target_group" "websocket" {
  name     = "crypto-trading-websocket"
  port     = 443
  protocol = "TLS"
  vpc_id   = module.aws_networking.vpc_id
  
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 10
    port                = "traffic-port"
    protocol            = "TCP"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  stickiness {
    type    = "source_ip"
    enabled = true
  }
  
  connection_termination = false
  preserve_client_ip     = true
  proxy_protocol_v2      = true
  
  tags = {
    Name = "crypto-trading-websocket-tg"
  }
}

# ALB Listeners
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.trading_api.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.trading_api.arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.trading_api.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# NLB Listener for WebSocket
resource "aws_lb_listener" "websocket" {
  load_balancer_arn = aws_lb.trading_websocket.arn
  port              = "443"
  protocol          = "TLS"
  certificate_arn   = aws_acm_certificate.trading_api.arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.websocket.arn
  }
}

# Path-based routing rules
resource "aws_lb_listener_rule" "api_v1" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  
  condition {
    path_pattern {
      values = ["/api/v1/*"]
    }
  }
}

resource "aws_lb_listener_rule" "websocket_upgrade" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 90
  
  action {
    type = "redirect"
    
    redirect {
      host        = aws_lb.trading_websocket.dns_name
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
  
  condition {
    http_header {
      http_header_name = "Upgrade"
      values          = ["websocket"]
    }
  }
}

# Rate limiting with AWS WAF
resource "aws_wafv2_web_acl" "rate_limit" {
  name  = "crypto-trading-rate-limit"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  rule {
    name     = "rate-limit-per-ip"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "rate-limit-per-ip"
      sampled_requests_enabled   = true
    }
  }
  
  rule {
    name     = "rate-limit-api-key"
    priority = 2
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 10000
        aggregate_key_type = "CUSTOM_KEYS"
        
        custom_key {
          header {
            name = "x-api-key"
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "rate-limit-api-key"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "crypto-trading-waf"
    sampled_requests_enabled   = true
  }
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.trading_api.arn
  web_acl_arn  = aws_wafv2_web_acl.rate_limit.arn
}

# GCP Load Balancer for multi-cloud
resource "google_compute_global_address" "trading_ip" {
  name = "crypto-trading-ip"
}

resource "google_compute_backend_service" "trading_api" {
  name                  = "crypto-trading-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  health_checks = [google_compute_health_check.api.id]
  
  backend {
    group           = google_compute_instance_group_manager.trading.instance_group
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
  
  circuit_breakers {
    max_connections             = 10000
    max_pending_requests       = 10000
    max_requests               = 10000
    max_requests_per_connection = 2
    max_retries                = 3
  }
  
  outlier_detection {
    consecutive_errors                    = 5
    consecutive_gateway_failure          = 5
    enforcing_consecutive_errors         = 100
    enforcing_consecutive_gateway_failure = 100
    enforcing_success_rate               = 100
    interval {
      seconds = 30
    }
    success_rate_minimum_hosts  = 3
    success_rate_request_volume = 100
  }
  
  security_settings {
    client_tls_policy = google_network_security_client_tls_policy.trading.id
  }
  
  cdn_policy {
    cache_mode = "CACHE_ALL_STATIC"
    default_ttl = 3600
    max_ttl     = 86400
    
    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = true
    }
  }
}

# URL Map for routing
resource "google_compute_url_map" "trading" {
  name            = "crypto-trading-url-map"
  default_service = google_compute_backend_service.trading_api.id
  
  host_rule {
    hosts        = ["api.${var.domain_name}"]
    path_matcher = "api"
  }
  
  path_matcher {
    name            = "api"
    default_service = google_compute_backend_service.trading_api.id
    
    path_rule {
      paths   = ["/ws/*"]
      service = google_compute_backend_service.websocket.id
    }
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "trading" {
  name             = "crypto-trading-https-proxy"
  url_map          = google_compute_url_map.trading.id
  ssl_certificates = [google_compute_managed_ssl_certificate.trading_api.id]
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "trading" {
  name       = "crypto-trading-forwarding-rule"
  target     = google_compute_target_https_proxy.trading.id
  port_range = "443"
  ip_address = google_compute_global_address.trading_ip.address
}

# Monitoring for load balancers
resource "aws_cloudwatch_dashboard" "load_balancing" {
  dashboard_name = "crypto-trading-load-balancing"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.trading_api.arn_suffix],
            [".", "ActiveConnectionCount", ".", "."],
            [".", "TargetResponseTime", ".", ".", { stat = "Average" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "ALB Metrics"
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/NetworkELB", "ActiveFlowCount", "LoadBalancer", aws_lb.trading_websocket.arn_suffix],
            [".", "ProcessedBytes", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "NLB WebSocket Metrics"
        }
      }
    ]
  })
}

# Outputs
output "global_accelerator_ips" {
  value = aws_globalaccelerator_accelerator.trading.ip_sets[0].ip_addresses
}

output "alb_dns_name" {
  value = aws_lb.trading_api.dns_name
}

output "nlb_dns_name" {
  value = aws_lb.trading_websocket.dns_name
}

output "gcp_load_balancer_ip" {
  value = google_compute_global_address.trading_ip.address
}