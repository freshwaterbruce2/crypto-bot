# Production Database Migration & Disaster Recovery Strategy

## Overview

This document outlines the comprehensive database migration strategy for the crypto trading platform, including multi-region replication, disaster recovery procedures, and zero-downtime migration approaches.

## Database Architecture

### Primary Database Configuration
- **Engine**: Amazon Aurora PostgreSQL 15.4
- **Instance Type**: db.r6g.2xlarge (3 instances)
- **Region**: US East 1 (Primary)
- **Storage**: Auto-scaling up to 128 TiB
- **Backup**: Continuous backup with 30-day retention
- **Point-in-Time Recovery**: Enabled (up to 35 days)

### Secondary Database (DR)
- **Region**: EU West 1
- **Instance Type**: db.r6g.xlarge (2 instances)
- **Replication**: Asynchronous with <1 second lag
- **Promotion Time**: <1 minute to become primary

## Migration Strategy

### Phase 1: Schema Migration

```sql
-- 1. Create production schema with partitioning
CREATE SCHEMA IF NOT EXISTS trading;

-- 2. Create partitioned tables for high-volume data
CREATE TABLE trading.orders (
    id BIGSERIAL,
    user_id UUID NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 3. Create monthly partitions
CREATE TABLE trading.orders_2024_01 PARTITION OF trading.orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 4. Create indexes for performance
CREATE INDEX idx_orders_user_created ON trading.orders (user_id, created_at);
CREATE INDEX idx_orders_symbol_status ON trading.orders (symbol, status);
CREATE INDEX idx_orders_status_created ON trading.orders (status, created_at)
    WHERE status IN ('PENDING', 'OPEN');

-- 5. Create hypertables for time-series data (if using TimescaleDB)
SELECT create_hypertable('trading.market_data', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);
```

### Phase 2: Data Migration Script

```python
#!/usr/bin/env python3
"""
Production Data Migration Script
Handles zero-downtime migration with validation
"""

import asyncio
import asyncpg
from datetime import datetime
import logging
from typing import Dict, List
import boto3

class DatabaseMigrator:
    def __init__(self, source_config: Dict, target_config: Dict):
        self.source = source_config
        self.target = target_config
        self.logger = logging.getLogger(__name__)
        
    async def migrate(self):
        """Execute full migration with validation"""
        try:
            # 1. Pre-migration validation
            await self.validate_source_database()
            
            # 2. Create target schema
            await self.create_target_schema()
            
            # 3. Enable CDC on source
            await self.enable_change_data_capture()
            
            # 4. Initial bulk copy
            await self.bulk_copy_data()
            
            # 5. Start CDC replication
            await self.start_cdc_replication()
            
            # 6. Validate data consistency
            await self.validate_migration()
            
            # 7. Switch application traffic
            await self.switch_traffic()
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            await self.rollback()
            raise
    
    async def validate_source_database(self):
        """Validate source database health and data integrity"""
        conn = await asyncpg.connect(**self.source)
        try:
            # Check table sizes
            tables = await conn.fetch("""
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            self.logger.info(f"Source database tables: {len(tables)}")
            
            # Verify no long-running transactions
            long_queries = await conn.fetch("""
                SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
                FROM pg_stat_activity 
                WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                AND state = 'active'
            """)
            
            if long_queries:
                raise Exception(f"Long-running queries detected: {long_queries}")
                
        finally:
            await conn.close()
    
    async def create_target_schema(self):
        """Create schema in target database"""
        conn = await asyncpg.connect(**self.target)
        try:
            with open('schema.sql', 'r') as f:
                schema_sql = f.read()
            
            await conn.execute(schema_sql)
            self.logger.info("Target schema created successfully")
            
        finally:
            await conn.close()
    
    async def bulk_copy_data(self):
        """Perform initial bulk data copy"""
        # Use AWS Database Migration Service for large datasets
        dms = boto3.client('dms')
        
        response = dms.create_replication_task(
            ReplicationTaskIdentifier='crypto-trading-migration',
            SourceEndpointArn='arn:aws:dms:us-east-1:123456789012:endpoint:source',
            TargetEndpointArn='arn:aws:dms:us-east-1:123456789012:endpoint:target',
            ReplicationInstanceArn='arn:aws:dms:us-east-1:123456789012:rep:instance',
            MigrationType='full-load-and-cdc',
            TableMappings='''
            {
                "rules": [{
                    "rule-type": "selection",
                    "rule-id": "1",
                    "rule-name": "1",
                    "object-locator": {
                        "schema-name": "public",
                        "table-name": "%"
                    },
                    "rule-action": "include"
                }]
            }
            '''
        )
        
        # Monitor migration progress
        await self.monitor_dms_task(response['ReplicationTask']['ReplicationTaskArn'])
```

### Phase 3: Disaster Recovery Procedures

```yaml
# Disaster Recovery Runbook
version: 1.0
procedures:
  - name: "Automated Failover"
    trigger: "Primary region failure"
    steps:
      - id: 1
        action: "Detect primary failure"
        automation: |
          Route53 health checks detect primary endpoint failure
          CloudWatch alarms triggered
          SNS notifications sent to on-call team
        sla: "< 30 seconds"
      
      - id: 2
        action: "Promote secondary cluster"
        automation: |
          aws rds promote-read-replica-db-cluster \
            --db-cluster-identifier crypto-trading-dr \
            --region eu-west-1
        sla: "< 60 seconds"
      
      - id: 3
        action: "Update DNS"
        automation: |
          Route53 automatically switches to DR endpoint
          based on health check failure
        sla: "< 90 seconds"
      
      - id: 4
        action: "Verify application connectivity"
        automation: |
          Synthetic monitoring validates API endpoints
          Dashboard updates with DR status
        sla: "< 2 minutes"
  
  - name: "Manual Failover"
    trigger: "Planned maintenance or testing"
    steps:
      - id: 1
        action: "Stop writes to primary"
        command: |
          kubectl scale deployment crypto-trading-bot --replicas=0
          
      - id: 2
        action: "Ensure replication caught up"
        command: |
          aws rds describe-db-clusters \
            --db-cluster-identifier crypto-trading-global \
            --query 'DBClusters[0].DBClusterMembers[?IsClusterWriter==`false`].PromotionTier'
            
      - id: 3
        action: "Promote DR cluster"
        command: |
          aws rds failover-db-cluster \
            --db-cluster-identifier crypto-trading-global \
            --target-db-instance-identifier crypto-trading-dr-instance-1
            
      - id: 4
        action: "Update application configuration"
        command: |
          kubectl set env deployment/crypto-trading-bot \
            DATABASE_ENDPOINT=crypto-trading-dr.cluster-xyz.eu-west-1.rds.amazonaws.com
            
      - id: 5
        action: "Resume application"
        command: |
          kubectl scale deployment crypto-trading-bot --replicas=3
```

### Phase 4: Backup and Recovery

```bash
#!/bin/bash
# Automated Backup Script

# Configuration
BACKUP_BUCKET="s3://crypto-trading-backups"
DB_ENDPOINT="crypto-trading.cluster-xyz.us-east-1.rds.amazonaws.com"
RETENTION_DAYS=30

# Function to perform backup
perform_backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="crypto_trading_backup_${TIMESTAMP}"
    
    # Create Aurora snapshot
    aws rds create-db-cluster-snapshot \
        --db-cluster-snapshot-identifier "${BACKUP_NAME}" \
        --db-cluster-identifier crypto-trading-prod \
        --tags Key=Type,Value=automated Key=Retention,Value=${RETENTION_DAYS}
    
    # Export to S3 for long-term storage
    aws rds start-export-task \
        --export-task-identifier "${BACKUP_NAME}_export" \
        --source-arn "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:${BACKUP_NAME}" \
        --s3-bucket-name crypto-trading-backups \
        --s3-prefix "aurora-exports/${TIMESTAMP}" \
        --iam-role-arn "arn:aws:iam::123456789012:role/rds-s3-export-role" \
        --kms-key-id "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    
    # Backup critical configuration
    kubectl get configmap -n crypto-trading -o yaml > "${BACKUP_NAME}_configmaps.yaml"
    kubectl get secret -n crypto-trading -o yaml > "${BACKUP_NAME}_secrets.yaml"
    
    # Encrypt and upload to S3
    tar czf - *.yaml | \
        openssl enc -aes-256-cbc -salt -pass pass:$ENCRYPTION_KEY | \
        aws s3 cp - "${BACKUP_BUCKET}/configs/${BACKUP_NAME}.tar.gz.enc"
    
    # Clean up old backups
    cleanup_old_backups
}

# Function to restore from backup
restore_from_backup() {
    BACKUP_ID=$1
    
    # Restore Aurora cluster
    aws rds restore-db-cluster-from-snapshot \
        --db-cluster-identifier crypto-trading-restored \
        --snapshot-identifier "${BACKUP_ID}" \
        --engine aurora-postgresql \
        --engine-version 15.4
    
    # Wait for cluster to be available
    aws rds wait db-cluster-available \
        --db-cluster-identifier crypto-trading-restored
    
    # Create instances
    for i in {1..3}; do
        aws rds create-db-instance \
            --db-instance-identifier "crypto-trading-restored-${i}" \
            --db-instance-class db.r6g.2xlarge \
            --engine aurora-postgresql \
            --db-cluster-identifier crypto-trading-restored
    done
    
    echo "Restore completed. Cluster endpoint: crypto-trading-restored.cluster-xyz.us-east-1.rds.amazonaws.com"
}

# Main execution
case "$1" in
    backup)
        perform_backup
        ;;
    restore)
        restore_from_backup "$2"
        ;;
    *)
        echo "Usage: $0 {backup|restore <backup-id>}"
        exit 1
        ;;
esac
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Replication Lag**
   - Alert threshold: > 1 second
   - Critical threshold: > 5 seconds

2. **Connection Pool Usage**
   - Alert threshold: > 80% utilized
   - Critical threshold: > 95% utilized

3. **Query Performance**
   - Slow query threshold: > 1 second
   - Alert on query queue depth > 10

4. **Storage Usage**
   - Alert threshold: > 80% used
   - Auto-scaling enabled up to 128 TiB

### CloudWatch Alarms

```terraform
resource "aws_cloudwatch_metric_alarm" "replication_lag" {
  alarm_name          = "crypto-trading-replication-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "AuroraReplicaLag"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "1000"  # 1 second in milliseconds
  alarm_description   = "Aurora replica lag exceeds 1 second"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    DBClusterIdentifier = "crypto-trading-prod"
  }
}
```

## Testing Procedures

### Disaster Recovery Testing

1. **Monthly DR Drills**
   - Perform controlled failover during maintenance window
   - Validate all services reconnect properly
   - Measure RTO (Recovery Time Objective) < 5 minutes
   - Measure RPO (Recovery Point Objective) < 1 minute

2. **Chaos Engineering**
   - Randomly terminate database connections
   - Simulate network partitions
   - Test split-brain scenarios
   - Validate automatic recovery

3. **Load Testing**
   ```bash
   # Run load test against DR region
   k6 run --vus 1000 --duration 30m load-test-dr.js
   ```

## Compliance and Audit

### Data Retention
- Transaction data: 7 years
- Audit logs: 5 years
- Backups: 1 year with monthly archives

### Encryption
- At-rest: AES-256 encryption using AWS KMS
- In-transit: TLS 1.3 for all connections
- Key rotation: Every 90 days

### Access Control
- IAM authentication for database access
- VPC security groups restrict network access
- Database activity monitoring enabled
- Audit logs sent to CloudWatch and S3