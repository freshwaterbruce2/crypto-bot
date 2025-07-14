# Crypto Trading Bot Code Improvement Prompt

## Context

I'm working on an automated cryptocurrency trading bot that interacts with exchanges (primarily Kraken) and executes trading strategies. The bot is experiencing issues with API connection reliability, strategy timeouts, and needs better error handling.

## Current Issues

Based on the logs, I'm seeing:

1. Connection issues with the Kraken API:
   ```
   [ERROR] [src.exchange.native_kraken_exchange] - [KRAKEN] Private request error: Cannot connect to host api.kraken.com:443 ssl:default [Timeout while contacting DNS servers]
   ```

2. Strategy timeout problems:
   ```
   [WARNING] [root] - [BOT] Strategy check timed out after 5s
   ```

3. Health monitoring warnings:
   ```
   [WARNING] [root] - [HEALTH] 1 unhealthy components: ['exchange']
   ```

## Improvement Goals

Please help me implement the following improvements to make the trading bot more robust:

1. **Implement Resilient API Connection Handling**:
   - Add proper retry logic with exponential backoff
   - Implement circuit breaker pattern for API endpoints
   - Handle DNS resolution failures explicitly
   - Add connection pooling if appropriate

2. **Fix Strategy Timeout Issues**:
   - Implement asynchronous strategy execution
   - Add proper timeout handling
   - Ensure strategies can be interrupted safely
   - Add monitoring for slow-running strategies

3. **Enhance Error Handling**:
   - Use specific exception types
   - Implement proper error recovery
   - Log all exceptions with context
   - Never swallow exceptions without handling

4. **Improve Health Monitoring**:
   - Create detailed health checks for each component
   - Add self-healing capabilities where possible
   - Implement proper alerting for persistent issues
   - Add metrics collection for system performance

## Key Files to Focus On

1. `src/exchange/native_kraken_exchange.py` - Needs improved connection handling
2. `src/trading/enhanced_balance_manager.py` - Should be resilient to API failures
3. `src/strategies/` - Fix timeout issues in strategy execution
4. Health monitoring system - Enhance with better diagnostics and recovery

## Implementation Guidelines

Please follow these guidelines when implementing the improvements:

1. **Safety First**: Never compromise safety for performance
2. **Resilience Over Speed**: The bot must be resilient to network issues, API failures, and unexpected market conditions
3. **Defensive Programming**: Assume all external inputs are potentially malicious or malformed
4. **Observability**: Every critical operation must be properly logged, monitored, and traceable

## Specific Implementation Requests

1. **For API Connection Issues**:
   - Implement a retry decorator with exponential backoff
   - Add a circuit breaker class to prevent overwhelming the API during outages
   - Handle DNS resolution failures with specific error messages and recovery logic
   - Add small delays (0.1-0.2s) between consecutive API calls

2. **For Strategy Timeouts**:
   - Convert synchronous strategy execution to asynchronous
   - Implement proper timeout handling with asyncio
   - Add monitoring for strategy execution times
   - Ensure strategies can be interrupted safely

3. **For Health Monitoring**:
   - Create a more detailed health check system
   - Add component-specific health metrics
   - Implement automatic recovery procedures where possible
   - Add better logging for health status changes

Please provide the implementation code with detailed comments explaining your approach. 