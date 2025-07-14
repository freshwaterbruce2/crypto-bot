# Self-Diagnostic & Self-Repair Flow

<!-- CLAUDE-note-diagnostic: Autonomous system health monitoring and self-healing capabilities -->
<!-- CLAUDE-note-repair: Automatic issue detection and resolution without human intervention -->

## Diagnostic Architecture

```python
class SelfDiagnosticSystem:
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.issue_detector = IssueDetector()
        self.repair_engine = SelfRepairEngine()
        self.recovery_procedures = RecoveryProcedures()
        self.diagnostic_interval = 30  # seconds
```

## Continuous Health Monitoring

### System Vitals Check
```python
async def monitor_system_vitals(self):
    """Real-time system health monitoring"""
    
    while True:
        vitals = {
            'websocket_status': await self.check_websocket_health(),
            'rate_limit_status': await self.check_rate_limit_health(),
            'portfolio_sync': await self.check_portfolio_sync(),
            'execution_latency': await self.measure_execution_latency(),
            'error_rate': await self.calculate_error_rate(),
            'memory_usage': await self.get_memory_usage(),
            'task_count': len(asyncio.all_tasks())
        }
        
        # Diagnose issues
        issues = await self.diagnose_issues(vitals)
        
        # Auto-repair if needed
        if issues:
            await self.initiate_self_repair(issues)
        
        await asyncio.sleep(self.diagnostic_interval)
```

### WebSocket Health Check
```python
async def check_websocket_health(self) -> Dict[str, Any]:
    """Comprehensive WebSocket connection diagnostics"""
    
    health_status = {
        'connected': False,
        'authenticated': False,
        'data_flowing': False,
        'latency_ms': 0,
        'reconnect_count': 0,
        'last_error': None
    }
```    
    try:
        # Check connection
        if self.websocket_manager.is_connected():
            health_status['connected'] = True
            
            # Check authentication
            if self.websocket_manager.is_authenticated():
                health_status['authenticated'] = True
                
                # Check data flow
                last_update = self.websocket_manager.last_data_timestamp
                if time.time() - last_update < 5:  # Data within 5 seconds
                    health_status['data_flowing'] = True
                
                # Measure latency
                health_status['latency_ms'] = await self.websocket_manager.ping()
        
        health_status['reconnect_count'] = self.websocket_manager.reconnect_count
        
    except Exception as e:
        health_status['last_error'] = str(e)
    
    return health_status
```

## Issue Detection

### Pattern-Based Detection
```python
async def diagnose_issues(self, vitals: Dict) -> List[Issue]:
    """Detect issues from system vitals"""
    
    issues = []
    
    # WebSocket issues
    if not vitals['websocket_status']['connected']:
        issues.append(Issue(
            type='websocket_disconnected',
            severity='critical',
            details=vitals['websocket_status']
        ))
    
    elif not vitals['websocket_status']['data_flowing']:
        issues.append(Issue(
            type='websocket_data_stale',
            severity='high',
            details={'last_update': vitals['websocket_status']['last_update']}
        ))
    
    # Rate limit issues
    for symbol, status in vitals['rate_limit_status'].items():
        if status['percentage'] > 85:
            issues.append(Issue(
                type='rate_limit_critical',
                severity='critical',
                symbol=symbol,
                details=status
            ))
```    
    # Performance issues
    if vitals['execution_latency'] > 2000:  # 2 seconds
        issues.append(Issue(
            type='high_latency',
            severity='medium',
            details={'latency_ms': vitals['execution_latency']}
        ))
    
    # Memory issues
    if vitals['memory_usage'] > 0.85:  # 85%
        issues.append(Issue(
            type='memory_pressure',
            severity='high',
            details={'usage_percent': vitals['memory_usage'] * 100}
        ))
    
    return issues
```

## Self-Repair Mechanisms

### Automated Repair Procedures
```python
async def initiate_self_repair(self, issues: List[Issue]):
    """Execute self-repair procedures for detected issues"""
    
    for issue in issues:
        try:
            if issue.type == 'websocket_disconnected':
                await self.repair_websocket_connection(issue)
            
            elif issue.type == 'websocket_data_stale':
                await self.refresh_websocket_subscriptions(issue)
            
            elif issue.type == 'rate_limit_critical':
                await self.handle_rate_limit_critical(issue)
            
            elif issue.type == 'high_latency':
                await self.optimize_for_latency(issue)
            
            elif issue.type == 'memory_pressure':
                await self.reduce_memory_usage(issue)
            
            # Log repair attempt
            await self.log_repair_attempt(issue)
            
        except Exception as e:
            # Escalate if repair fails
            await self.escalate_issue(issue, e)
```
### WebSocket Repair
```python
async def repair_websocket_connection(self, issue: Issue):
    """Repair WebSocket connection issues"""
    
    # Check API permissions first
    if not await self.verify_websocket_permissions():
        raise Exception("WebSocket API permission not enabled in Kraken Pro")
    
    # Generate fresh token
    token = await self.get_fresh_websocket_token()
    
    # Reconnect with exponential backoff
    for attempt in range(5):
        try:
            await self.websocket_manager.disconnect()
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            await self.websocket_manager.connect(
                url='wss://ws-auth.kraken.com/v2',
                token=token
            )
            
            # Verify connection
            if await self.websocket_manager.verify_connection():
                await self.resubscribe_all_channels()
                return
                
        except Exception as e:
            if attempt == 4:  # Last attempt
                raise Exception(f"WebSocket repair failed after 5 attempts: {e}")
```

### Rate Limit Recovery
```python
async def handle_rate_limit_critical(self, issue: Issue):
    """Handle critical rate limit situations"""
    
    symbol = issue.symbol
    
    # Immediate actions
    await self.pause_trading_on_symbol(symbol)
    
    # Cancel young orders if necessary
    open_orders = await self.get_open_orders(symbol)
    for order in open_orders:
        age = time.time() - order.timestamp
        if age > 300:  # Only cancel orders older than 5 minutes
            await self.safe_cancel_order(order)
            await asyncio.sleep(1)  # Delay between cancels
```    
    # Switch to IOC orders
    self.execution_params[symbol]['use_ioc'] = True
    
    # Calculate recovery time
    recovery_time = await self.rate_limiter.estimate_recovery_time(symbol)
    
    # Schedule resume
    asyncio.create_task(self.resume_trading_after_delay(symbol, recovery_time))
```

## Self-Optimization

### Performance Auto-Tuning
```python
async def auto_tune_performance(self):
    """Automatically tune system for optimal performance"""
    
    # Analyze recent performance
    metrics = await self.get_performance_metrics(hours=24)
    
    # Adjust parameters based on metrics
    if metrics.avg_execution_time > 1.5:
        # Reduce API call frequency
        self.scan_interval = min(self.scan_interval * 1.2, 15)
    
    if metrics.success_rate < 0.9:
        # Increase order size buffer
        self.min_order_buffer = 1.2  # 20% buffer
    
    if metrics.websocket_reconnects > 5:
        # Increase connection stability measures
        self.websocket_manager.heartbeat_interval = 20
        self.websocket_manager.enable_connection_pooling = True
```

### Resource Optimization
```python
async def optimize_resource_usage(self):
    """Optimize system resource usage"""
    
    # Analyze resource patterns
    usage_pattern = await self.analyze_resource_usage_pattern()
    
    # Adjust based on patterns
    if usage_pattern.peak_memory_time:
        # Schedule heavy operations outside peak times
        self.schedule_maintenance_window(usage_pattern.low_usage_time)
    
    # Implement dynamic scaling
    if usage_pattern.avg_cpu > 70:
        await self.reduce_concurrent_operations()
    elif usage_pattern.avg_cpu < 30:
        await self.increase_concurrent_operations()
```
## Recovery Procedures

### Emergency Recovery
```python
async def emergency_recovery_procedure(self):
    """Complete system recovery procedure"""
    
    logger.critical("Initiating emergency recovery procedure")
    
    # 1. Stop all trading
    await self.emergency_stop_all_trading()
    
    # 2. Disconnect all connections
    await self.disconnect_all_services()
    
    # 3. Clear corrupted data
    await self.clear_corrupted_caches()
    
    # 4. Restart core services
    await self.restart_core_services()
    
    # 5. Verify system health
    health_check = await self.comprehensive_health_check()
    
    if health_check.passed:
        # 6. Gradually resume operations
        await self.gradual_resume_operations()
    else:
        # 7. Safe mode operation
        await self.enter_safe_mode()
```