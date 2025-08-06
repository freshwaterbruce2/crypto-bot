# Production Database Configuration with Multi-Region Replication
# High-availability database setup for crypto trading platform

# Primary RDS Aurora Global Database (AWS)
resource "aws_rds_global_cluster" "trading_db" {
  global_cluster_identifier = "crypto-trading-global"
  engine                    = "aurora-postgresql"
  engine_version           = "15.4"
  database_name            = "trading_platform"
  storage_encrypted        = true
  
  lifecycle {
    prevent_destroy = true
  }
}

# Primary Region Aurora Cluster
resource "aws_rds_cluster" "primary" {
  cluster_identifier      = "crypto-trading-primary"
  engine                  = "aurora-postgresql"
  engine_version         = "15.4"
  engine_mode            = "provisioned"
  database_name          = "trading_platform"
  master_username        = "trading_admin"
  master_password        = random_password.db_password.result
  
  global_cluster_identifier = aws_rds_global_cluster.trading_db.id
  
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.trading.name
  db_subnet_group_name           = aws_db_subnet_group.trading.name
  
  backup_retention_period      = 30
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  
  enabled_cloudwatch_logs_exports = [
    "postgresql"
  ]
  
  storage_encrypted               = true
  kms_key_id                     = aws_kms_key.rds.arn
  apply_immediately              = false
  final_snapshot_identifier      = "crypto-trading-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  skip_final_snapshot            = false
  copy_tags_to_snapshot          = true
  deletion_protection            = true
  
  serverlessv2_scaling_configuration {
    max_capacity = 16
    min_capacity = 2
  }
  
  tags = {
    Name        = "crypto-trading-primary-db"
    Environment = "production"
  }
}

# Aurora Serverless v2 Instances
resource "aws_rds_cluster_instance" "primary_instances" {
  count              = 3
  identifier         = "crypto-trading-${count.index}"
  cluster_identifier = aws_rds_cluster.primary.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.primary.engine
  engine_version     = aws_rds_cluster.primary.engine_version
  
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  monitoring_interval         = 60
  monitoring_role_arn        = aws_iam_role.rds_monitoring.arn
  
  tags = {
    Name = "crypto-trading-instance-${count.index}"
  }
}

# Secondary Region Aurora Cluster (Disaster Recovery)
resource "aws_rds_cluster" "secondary" {
  provider = aws.secondary
  
  cluster_identifier      = "crypto-trading-secondary"
  engine                  = "aurora-postgresql"
  engine_version         = "15.4"
  engine_mode            = "provisioned"
  
  global_cluster_identifier = aws_rds_global_cluster.trading_db.id
  
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.trading_secondary.name
  db_subnet_group_name           = aws_db_subnet_group.trading_secondary.name
  
  backup_retention_period      = 30
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  
  storage_encrypted               = true
  kms_key_id                     = aws_kms_key.rds_secondary.arn
  
  serverlessv2_scaling_configuration {
    max_capacity = 8
    min_capacity = 1
  }
  
  depends_on = [aws_rds_cluster.primary]
  
  tags = {
    Name        = "crypto-trading-secondary-db"
    Environment = "production"
  }
}

# Database Parameter Groups
resource "aws_rds_cluster_parameter_group" "trading" {
  family = "aurora-postgresql15"
  name   = "crypto-trading-params"
  
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgaudit,pg_cron"
  }
  
  parameter {
    name  = "log_statement"
    value = "all"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }
  
  parameter {
    name  = "autovacuum_max_workers"
    value = "5"
  }
  
  parameter {
    name  = "max_connections"
    value = "1000"
  }
}

# Database Migration Service (DMS) for initial migration
resource "aws_dms_replication_instance" "trading" {
  replication_instance_class   = "dms.r5.xlarge"
  replication_instance_id      = "crypto-trading-migration"
  allocated_storage           = 100
  multi_az                    = true
  publicly_accessible         = false
  
  vpc_security_group_ids = [aws_security_group.dms.id]
  replication_subnet_group_id = aws_dms_replication_subnet_group.trading.id
  
  tags = {
    Name = "crypto-trading-dms"
  }
}

# DMS Source Endpoint (existing database)
resource "aws_dms_endpoint" "source" {
  endpoint_id   = "crypto-trading-source"
  endpoint_type = "source"
  engine_name   = "postgres"
  
  server_name = var.source_db_host
  port        = var.source_db_port
  username    = var.source_db_username
  password    = var.source_db_password
  database_name = var.source_db_name
  
  ssl_mode = "require"
  
  tags = {
    Name = "crypto-trading-source-db"
  }
}

# DMS Target Endpoint (Aurora)
resource "aws_dms_endpoint" "target" {
  endpoint_id   = "crypto-trading-target"
  endpoint_type = "target"
  engine_name   = "aurora-postgresql"
  
  server_name = aws_rds_cluster.primary.endpoint
  port        = 5432
  username    = aws_rds_cluster.primary.master_username
  password    = aws_rds_cluster.primary.master_password
  database_name = aws_rds_cluster.primary.database_name
  
  ssl_mode = "require"
  
  tags = {
    Name = "crypto-trading-target-db"
  }
}

# DMS Migration Task
resource "aws_dms_replication_task" "trading" {
  migration_type           = "full-load-and-cdc"
  replication_instance_arn = aws_dms_replication_instance.trading.replication_instance_arn
  replication_task_id      = "crypto-trading-migration-task"
  
  source_endpoint_arn = aws_dms_endpoint.source.endpoint_arn
  target_endpoint_arn = aws_dms_endpoint.target.endpoint_arn
  
  table_mappings = jsonencode({
    rules = [{
      rule-type = "selection"
      rule-id   = "1"
      rule-name = "1"
      object-locator = {
        schema-name = "%"
        table-name  = "%"
      }
      rule-action = "include"
    }]
  })
  
  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchema         = ""
      SupportLobs          = true
      FullLobMode          = false
      LobChunkSize         = 0
      LimitedSizeLobMode   = true
      LobMaxSize           = 32
      InlineLobMaxSize     = 0
      LoadMaxFileSize      = 0
      ParallelLoadThreads  = 0
      ParallelLoadBufferSize = 0
      ParallelLoadQueuesPerThread = 0
      ParallelApplyThreads = 0
      ParallelApplyBufferSize = 0
      ParallelApplyQueuesPerThread = 0
    }
    FullLoadSettings = {
      TargetTablePrepMode = "DROP_AND_CREATE"
      CreatePkAfterFullLoad = false
      StopTaskCachedChangesApplied = false
      StopTaskCachedChangesNotApplied = false
      MaxFullLoadSubTasks = 8
      TransactionConsistencyTimeout = 600
      CommitRate = 10000
    }
    Logging = {
      EnableLogging = true
      LogComponents = [{
        Id       = "TRANSFORMATION"
        Severity = "LOGGER_SEVERITY_DEFAULT"
      }]
    }
  })
  
  tags = {
    Name = "crypto-trading-migration"
  }
}

# Redis Cluster for High-Performance Caching
resource "aws_elasticache_replication_group" "trading_cache" {
  replication_group_id       = "crypto-trading-cache"
  description               = "Redis cluster for trading platform"
  engine                    = "redis"
  node_type                 = "cache.r6g.xlarge"
  parameter_group_name      = aws_elasticache_parameter_group.trading.name
  port                      = 6379
  
  # Multi-AZ with automatic failover
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  # Cluster mode enabled for sharding
  num_node_groups         = 3
  replicas_per_node_group = 2
  
  subnet_group_name = aws_elasticache_subnet_group.trading.name
  security_group_ids = [aws_security_group.redis.id]
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = random_password.redis_auth.result
  
  # Backups
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  
  # Maintenance
  maintenance_window = "sun:05:00-sun:07:00"
  notification_topic_arn = aws_sns_topic.database_alerts.arn
  
  # Engine version
  engine_version = "7.0"
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format      = "json"
    log_type        = "slow-log"
  }
  
  tags = {
    Name        = "crypto-trading-cache"
    Environment = "production"
  }
}

# TimescaleDB for Time-Series Data
resource "kubernetes_stateful_set" "timescaledb" {
  metadata {
    name      = "timescaledb"
    namespace = "trading-system"
  }
  
  spec {
    service_name = "timescaledb"
    replicas     = 3
    
    selector {
      match_labels = {
        app = "timescaledb"
      }
    }
    
    template {
      metadata {
        labels = {
          app = "timescaledb"
        }
      }
      
      spec {
        container {
          name  = "timescaledb"
          image = "timescale/timescaledb-ha:pg15-latest"
          
          port {
            container_port = 5432
            name          = "postgres"
          }
          
          env {
            name  = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = "timescaledb-credentials"
                key  = "password"
              }
            }
          }
          
          env {
            name  = "POSTGRES_DB"
            value = "trading_timeseries"
          }
          
          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }
          
          resources {
            requests = {
              cpu    = "2"
              memory = "8Gi"
            }
            limits = {
              cpu    = "4"
              memory = "16Gi"
            }
          }
          
          liveness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 30
            period_seconds       = 10
          }
          
          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 5
            period_seconds       = 5
          }
        }
      }
    }
    
    volume_claim_template {
      metadata {
        name = "data"
      }
      
      spec {
        access_modes = ["ReadWriteOnce"]
        storage_class_name = "fast-ssd"
        
        resources {
          requests = {
            storage = "100Gi"
          }
        }
      }
    }
  }
}

# Database Backup Strategy
resource "aws_backup_plan" "trading_db" {
  name = "crypto-trading-db-backup"
  
  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.trading.name
    schedule          = "cron(0 3 * * ? *)"
    
    lifecycle {
      delete_after = 30
    }
    
    recovery_point_tags = {
      Environment = "production"
      Type        = "daily"
    }
  }
  
  rule {
    rule_name         = "weekly_backups"
    target_vault_name = aws_backup_vault.trading.name
    schedule          = "cron(0 3 ? * SUN *)"
    
    lifecycle {
      delete_after = 90
      cold_storage_after = 30
    }
    
    recovery_point_tags = {
      Environment = "production"
      Type        = "weekly"
    }
  }
  
  rule {
    rule_name         = "monthly_backups"
    target_vault_name = aws_backup_vault.trading.name
    schedule          = "cron(0 3 1 * ? *)"
    
    lifecycle {
      delete_after = 365
      cold_storage_after = 90
    }
    
    recovery_point_tags = {
      Environment = "production"
      Type        = "monthly"
    }
  }
}

# Monitoring and Alerts
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "trading-db-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Database CPU utilization"
  alarm_actions       = [aws_sns_topic.database_alerts.arn]
  
  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.primary.cluster_identifier
  }
}

# Outputs
output "primary_db_endpoint" {
  value = aws_rds_cluster.primary.endpoint
  sensitive = true
}

output "secondary_db_endpoint" {
  value = aws_rds_cluster.secondary.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.trading_cache.configuration_endpoint_address
  sensitive = true
}