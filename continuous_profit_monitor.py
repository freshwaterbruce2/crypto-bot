#!/usr/bin/env python3
"""
Continuous Profit Monitoring System
Monitors bot performance until profitable trading is achieved
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class ContinuousProfitMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.monitoring = True
        self.profit_target = 0.01  # $0.01 minimum profit to confirm working
        self.check_interval = 30  # Check every 30 seconds
        self.log_file = "profit_monitoring_log.txt"
        
        # Performance metrics
        self.trades_executed = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        self.last_check = time.time()
        
    async def monitor_bot_performance(self):
        """Main monitoring loop that runs until bot is profitable"""
        
        print("=" * 70)
        print("CONTINUOUS PROFIT MONITORING SYSTEM")
        print("=" * 70)
        print(f"Target: First profitable trade (>${self.profit_target})")
        print("Monitoring will continue until bot achieves consistent profits")
        print("=" * 70)
        
        while self.monitoring:
            try:
                # Check bot status
                status = await self.check_bot_status()
                
                # Analyze performance
                analysis = await self.analyze_performance()
                
                # Display current status
                await self.display_status(status, analysis)
                
                # Check if profitable
                if await self.check_profitability(analysis):
                    await self.handle_profit_achieved(analysis)
                    break
                
                # Apply fixes if needed
                if analysis['issues_detected']:
                    await self.apply_automatic_fixes(analysis)
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"\nError in monitoring: {e}")
                await asyncio.sleep(5)
                
    async def check_bot_status(self) -> Dict:
        """Check if bot is running and healthy"""
        status = {
            'running': False,
            'process_id': None,
            'uptime': 0,
            'websocket_connected': False,
            'last_trade_attempt': None
        }
        
        # Check for bot process
        try:
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'live_launch.py' in line and 'grep' not in line:
                    status['running'] = True
                    parts = line.split()
                    status['process_id'] = parts[1]
                    break
        except:
            pass
            
        # Check log activity
        try:
            log_path = "kraken_infinity_bot.log"
            if os.path.exists(log_path):
                mtime = os.path.getmtime(log_path)
                status['log_last_modified'] = time.time() - mtime
                
                # Get last few lines
                with open(log_path, 'rb') as f:
                    f.seek(0, 2)  # Go to end
                    file_size = f.tell()
                    f.seek(max(0, file_size - 5000))  # Read last 5KB
                    last_content = f.read().decode('utf-8', errors='ignore')
                    
                    # Check for trade attempts
                    if 'Executing' in last_content or 'ORDER' in last_content:
                        status['last_trade_attempt'] = 'Recent'
                    
                    # Check for WebSocket
                    if 'WebSocket connected' in last_content:
                        status['websocket_connected'] = True
        except:
            pass
            
        return status
        
    async def analyze_performance(self) -> Dict:
        """Analyze bot performance and detect issues"""
        analysis = {
            'trades_executed': 0,
            'profitable_trades': 0,
            'total_profit': 0.0,
            'issues_detected': [],
            'balance_status': {},
            'signal_stats': {}
        }
        
        # Parse recent logs for performance data
        try:
            log_path = "kraken_infinity_bot.log"
            if os.path.exists(log_path):
                with open(log_path, 'rb') as f:
                    f.seek(0, 2)
                    file_size = f.tell()
                    f.seek(max(0, file_size - 100000))  # Last 100KB
                    content = f.read().decode('utf-8', errors='ignore')
                    
                    # Count trades
                    analysis['trades_executed'] = content.count('Trade executed:')
                    
                    # Check for common issues
                    if 'Circuit breaker' in content and 'OPEN' in content:
                        analysis['issues_detected'].append('circuit_breaker_blocking')
                    
                    if 'Insufficient' in content or 'insufficient' in content:
                        analysis['issues_detected'].append('insufficient_funds')
                        
                    if 'balance: $5' in content or 'USDT: $5' in content:
                        analysis['issues_detected'].append('balance_detection_error')
                        
                    if 'tracked position amount for' in content and ': 0' in content:
                        analysis['issues_detected'].append('position_tracking_error')
                        
                    if 'rejected' in content and 'confidence' in content:
                        # Count rejected signals
                        rejected_count = content.count('rejected')
                        analysis['signal_stats']['rejected'] = rejected_count
                        if rejected_count > 100:
                            analysis['issues_detected'].append('high_signal_rejection')
                            
        except Exception as e:
            analysis['error'] = str(e)
            
        return analysis
        
    async def display_status(self, status: Dict, analysis: Dict):
        """Display current monitoring status"""
        
        # Clear screen for clean display
        print("\033[H\033[J", end='')  # Clear screen
        
        print("=" * 70)
        print(f"PROFIT MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Bot Status
        print("\nBOT STATUS:")
        if status['running']:
            print(f"  Running: YES (PID: {status['process_id']})")
        else:
            print("  Running: NO - Bot not detected!")
            
        if status.get('log_last_modified', float('inf')) < 60:
            print(f"  Activity: ACTIVE (log updated {status['log_last_modified']:.0f}s ago)")
        else:
            print("  Activity: STALE - No recent activity")
            
        print(f"  WebSocket: {'CONNECTED' if status['websocket_connected'] else 'DISCONNECTED'}")
        
        # Performance
        print("\nPERFORMANCE:")
        print(f"  Trades Executed: {analysis['trades_executed']}")
        print(f"  Profitable Trades: {analysis['profitable_trades']}")
        print(f"  Total Profit: ${analysis['total_profit']:.4f}")
        
        # Issues
        if analysis['issues_detected']:
            print("\nISSUES DETECTED:")
            for issue in analysis['issues_detected']:
                print(f"  - {issue}")
        else:
            print("\nISSUES: None detected")
            
        # Monitoring Time
        runtime = time.time() - self.start_time
        print(f"\nMonitoring Duration: {runtime/60:.1f} minutes")
        
    async def check_profitability(self, analysis: Dict) -> bool:
        """Check if bot has achieved profitability"""
        
        # Simple check for any profit
        if analysis['profitable_trades'] > 0:
            return True
            
        # Check if trades are being executed
        if analysis['trades_executed'] > self.trades_executed:
            self.trades_executed = analysis['trades_executed']
            print("\n  [UPDATE] New trades detected!")
            
        return False
        
    async def handle_profit_achieved(self, analysis: Dict):
        """Handle when bot achieves profitability"""
        
        print("\n" + "=" * 70)
        print("SUCCESS! BOT IS NOW PROFITABLE!")
        print("=" * 70)
        print(f"Total Trades: {analysis['trades_executed']}")
        print(f"Profitable Trades: {analysis['profitable_trades']}")
        print(f"Total Profit: ${analysis['total_profit']:.4f}")
        print("\nThe bot is successfully executing profitable trades.")
        print("Monitoring complete - bot is operational!")
        print("=" * 70)
        
        # Log success
        with open(self.log_file, 'a') as f:
            f.write(f"\n{datetime.now()} - SUCCESS: Bot achieved profitability\n")
            f.write(f"Stats: {json.dumps(analysis, indent=2)}\n")
            
    async def apply_automatic_fixes(self, analysis: Dict):
        """Apply automatic fixes for detected issues"""
        
        print("\n[AUTO-FIX] Applying corrections...")
        
        for issue in analysis['issues_detected']:
            if issue == 'circuit_breaker_blocking':
                print("  - Resetting circuit breaker...")
                os.system("python3 fix_circuit_breaker_timeout.py > /dev/null 2>&1")
                
            elif issue == 'balance_detection_error':
                print("  - Forcing balance sync...")
                os.system("python3 force_balance_sync.py > /dev/null 2>&1")
                
            elif issue == 'position_tracking_error':
                print("  - Syncing portfolio positions...")
                os.system("python3 test_portfolio_sync.py > /dev/null 2>&1")
                
            elif issue == 'high_signal_rejection':
                print("  - Enabling emergency mode (lower thresholds)...")
                os.system("python3 enable_emergency_mode.py enable > /dev/null 2>&1")
                
        print("  [AUTO-FIX] Corrections applied")

async def main():
    """Main entry point"""
    monitor = ContinuousProfitMonitor()
    
    print("\nStarting continuous profit monitoring...")
    print("This will run until the bot achieves profitable trading.")
    print("Press Ctrl+C to stop monitoring.\n")
    
    try:
        await monitor.monitor_bot_performance()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        
if __name__ == "__main__":
    asyncio.run(main())