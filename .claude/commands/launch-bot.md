# Launch Trading Bot

Safe launch sequence for the Kraken trading bot with pre-flight checks.

## Command Usage
`/launch-bot [mode]`

## Action
Execute complete launch sequence with safety checks and monitoring.

Launch modes for $ARGUMENTS:
- **live**: Full production launch with real trading
- **test**: Test launch with validation checks only
- **debug**: Debug mode with enhanced logging
- **recovery**: Recovery launch after crash or restart

Pre-flight sequence:
1. Verify all dependencies and SDK versions
2. Check API credentials and permissions
3. Test WebSocket connectivity and data flow
4. Validate configuration and risk parameters
5. Ensure clean state (no conflicting processes)
6. Initialize all components in correct order
7. Verify signal generation pipeline
8. Monitor initial startup logs for errors

Safety checks:
- Confirm stop-loss and risk limits are active
- Verify position sizing is within safe limits
- Check balance thresholds and emergency stops
- Ensure proper error handling and logging

Provide real-time status updates and stop immediately if any critical issues are detected.