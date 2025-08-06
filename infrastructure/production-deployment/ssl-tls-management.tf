# SSL/TLS Certificate Management Configuration
# Automated certificate provisioning and renewal for trading APIs

# AWS Certificate Manager for ALB/CloudFront
resource "aws_acm_certificate" "trading_api" {
  domain_name       = var.domain_name
  validation_method = "DNS"
  
  subject_alternative_names = [
    "*.${var.domain_name}",
    "api.${var.domain_name}",
    "ws.${var.domain_name}",
    "admin.${var.domain_name}"
  ]
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = {
    Name        = "crypto-trading-api-cert"
    Environment = "production"
  }
}

# Route53 DNS validation for ACM
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.trading_api.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

# Certificate validation
resource "aws_acm_certificate_validation" "trading_api" {
  certificate_arn         = aws_acm_certificate.trading_api.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# GCP Managed SSL Certificate
resource "google_compute_managed_ssl_certificate" "trading_api" {
  name = "crypto-trading-api-cert"
  
  managed {
    domains = [
      var.domain_name,
      "api.${var.domain_name}",
      "ws.${var.domain_name}"
    ]
  }
}

# Let's Encrypt Certificate for Kubernetes Ingress
resource "kubernetes_manifest" "cert_manager" {
  manifest = {
    apiVersion = "v1"
    kind       = "Namespace"
    metadata = {
      name = "cert-manager"
    }
  }
}

# Install cert-manager using Helm
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = "v1.13.0"
  namespace  = "cert-manager"
  
  set {
    name  = "installCRDs"
    value = "true"
  }
  
  set {
    name  = "global.leaderElection.namespace"
    value = "cert-manager"
  }
  
  depends_on = [kubernetes_manifest.cert_manager]
}

# ClusterIssuer for Let's Encrypt
resource "kubernetes_manifest" "letsencrypt_prod" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-prod"
    }
    spec = {
      acme = {
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.cert_admin_email
        privateKeySecretRef = {
          name = "letsencrypt-prod"
        }
        solvers = [{
          http01 = {
            ingress = {
              class = "nginx"
            }
          }
        }]
      }
    }
  }
  
  depends_on = [helm_release.cert_manager]
}

# Certificate for Trading API
resource "kubernetes_manifest" "trading_api_cert" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "Certificate"
    metadata = {
      name      = "trading-api-tls"
      namespace = "trading-system"
    }
    spec = {
      secretName = "trading-api-tls"
      issuerRef = {
        name = "letsencrypt-prod"
        kind = "ClusterIssuer"
      }
      commonName = "api.${var.domain_name}"
      dnsNames = [
        "api.${var.domain_name}",
        "ws.${var.domain_name}",
        "admin.${var.domain_name}"
      ]
    }
  }
  
  depends_on = [kubernetes_manifest.letsencrypt_prod]
}

# mTLS Configuration for Service Mesh
resource "kubernetes_manifest" "mtls_policy" {
  manifest = {
    apiVersion = "security.istio.io/v1beta1"
    kind       = "PeerAuthentication"
    metadata = {
      name      = "default"
      namespace = "trading-system"
    }
    spec = {
      mtls = {
        mode = "STRICT"
      }
    }
  }
}

# Certificate rotation automation
resource "kubernetes_cron_job_v1" "cert_rotation" {
  metadata {
    name      = "cert-rotation"
    namespace = "cert-manager"
  }
  
  spec {
    schedule = "0 0 * * 0"  # Weekly
    
    job_template {
      metadata {}
      
      spec {
        template {
          metadata {}
          
          spec {
            container {
              name  = "cert-checker"
              image = "bitnami/kubectl:latest"
              
              command = ["/bin/sh", "-c"]
              args = [
                <<-EOT
                # Check certificate expiration
                kubectl get certificates -A -o json | \
                jq -r '.items[] | select(.status.renewalTime < (now + 2592000 | todate)) | 
                "\(.metadata.namespace)/\(.metadata.name)"' | \
                while read cert; do
                  kubectl annotate certificate $cert cert-manager.io/issue-temporary-certificate="true" --overwrite
                done
                EOT
              ]
            }
            
            restart_policy = "OnFailure"
            
            service_account_name = "cert-rotation"
          }
        }
      }
    }
  }
}

# WAF Rules for SSL/TLS Security
resource "aws_wafv2_web_acl" "trading_api" {
  name  = "crypto-trading-api-waf"
  scope = "CLOUDFRONT"
  
  default_action {
    allow {}
  }
  
  # Enforce HTTPS only
  rule {
    name     = "enforce-https"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      not_statement {
        statement {
          byte_match_statement {
            search_string = "https"
            field_to_match {
              single_header {
                name = "x-forwarded-proto"
              }
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
            positional_constraint = "EXACTLY"
          }
        }
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "enforce-https"
      sampled_requests_enabled   = true
    }
  }
  
  # Block outdated TLS versions
  rule {
    name     = "block-old-tls"
    priority = 2
    
    action {
      block {}
    }
    
    statement {
      byte_match_statement {
        search_string = "TLSv1.0\nTLSv1.1"
        field_to_match {
          single_header {
            name = "x-amzn-tls-version"
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
        positional_constraint = "CONTAINS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "block-old-tls"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "crypto-trading-api-waf"
    sampled_requests_enabled   = true
  }
}

# SSL/TLS monitoring dashboard
resource "aws_cloudwatch_dashboard" "ssl_monitoring" {
  dashboard_name = "ssl-tls-monitoring"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/CertificateManager", "DaysToExpiry", "CertificateArn", aws_acm_certificate.trading_api.arn]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Certificate Days to Expiry"
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/CloudFront", "4xxErrorRate", "DistributionId", aws_cloudfront_distribution.trading_api.id],
            [".", "5xxErrorRate", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = "us-east-1"
          title  = "SSL/TLS Error Rates"
        }
      }
    ]
  })
}

# Outputs
output "acm_certificate_arn" {
  value = aws_acm_certificate.trading_api.arn
}

output "acm_certificate_status" {
  value = aws_acm_certificate.trading_api.status
}

output "gcp_ssl_certificate_id" {
  value = google_compute_managed_ssl_certificate.trading_api.id
}