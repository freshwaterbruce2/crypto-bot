#!/usr/bin/env python3
"""
Production Trading Monitor - Real-time Dashboard
Tracks balance accuracy, trade execution, and profit accumulation
"""

import asyncio
import time
import os
import sys
from datetime import datetime
from decimal import Decimal
from collections import deque
import logging
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTradingMonitor:
    """Simplified trading monitor focused on key metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.trades = deque(maxlen=1000)
        self.balance_updates = deque(maxlen=100)
        self.signals = deque(maxlen=100)
        self.errors = deque(maxlen=50)
        self.last_balance = None
        self.total_profit = Decimal("0")
        self.trade_count = 0
        
    async def monitor_trading(self):
        """Main monitoring loop"""
        print("\n" + "="*60)
        print("KRAKEN TRADING BOT - LIVE MONITOR")
        print("="*60)
        print(f"Started: {datetime.now()}")
        print("Tracking: Balance | Trades | Profits | Errors")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                # Read latest log entries
                await self.analyze_logs()
                
                # Display dashboard
                self.display_dashboard()
                
                # Wait before next update
                await asyncio.sleep(3)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def analyze_logs(self):
        """Analyze recent log entries"""
        log_file = PROJECT_ROOT / "kraken_bot.log"
        
        if not log_file.exists():
            return
            
        try:
            # Read last 500 lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-500:]
            
            for line in lines:
                # Balance updates
                if "[BALANCE_FIX]" in line:
                    self.process_balance_update(line)
                
                # Trade executions
                elif "Order placed successfully" in line:
                    self.process_trade(line)
                
                # Signal generation
                elif "[SIGNAL]" in line or "Evaluating signal" in line:
                    self.process_signal(line)
                
                # Errors
                elif "ERROR" in line:
                    self.process_error(line)
                    
        except Exception as e:
            logger.debug(f"Log analysis error: {e}")
    
    def process_balance_update(self, line: str):
        """Process balance update"""
        try:
            if "Fresh balance" in line and "$" in line:
                # Extract balance amount
                parts = line.split("$")
                if len(parts) > 1:
                    balance_str = parts[1].split()[0].replace(",", "")
                    balance = float(balance_str)
                    
                    self.balance_updates.append({
                        'time': datetime.now(),
                        'balance': balance
                    })
                    self.last_balance = balance
        except:
            pass
    
    def process_trade(self, line: str):
        """Process trade execution"""
        try:
            # Extract trade details
            self.trades.append({
                'time': datetime.now(),
                'details': line.strip()
            })
            self.trade_count += 1
        except:
            pass
    
    def process_signal(self, line: str):
        """Process signal generation"""
        try:
            self.signals.append({
                'time': datetime.now(),
                'signal': line.strip()
            })
        except:
            pass
    
    def process_error(self, line: str):
        """Process error"""
        try:
            self.errors.append({
                'time': datetime.now(),
                'error': line.strip()
            })
        except:
            pass
    
    def display_dashboard(self):
        """Display monitoring dashboard"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("="*60)
        print("KRAKEN TRADING BOT - LIVE MONITOR")
        print("="*60)
        print(f"Running for: {self.format_uptime()}")
        print()
        
        # Balance Status
        print("BALANCE STATUS:")
        print("-" * 40)
        if self.last_balance:
            print(f"Current Balance: ${self.last_balance:.2f}")
            # Check for cache issue
            if self.last_balance < 5:
                print("⚠️  WARNING: Balance may be cached (showing < $5)")
            else:
                print("✅ Balance looks correct")
        else:
            print("Waiting for balance update...")
        
        # Recent balance history
        if len(self.balance_updates) > 1:
            print("\nRecent Updates:")
            for update in list(self.balance_updates)[-3:]:
                print(f"  {update['time'].strftime('%H:%M:%S')} - ${update['balance']:.2f}")
        
        # Trading Activity
        print("\nTRADING ACTIVITY:")
        print("-" * 40)
        print(f"Total Trades: {self.trade_count}")
        print(f"Signals Generated: {len(self.signals)}")
        
        # Recent signals
        if self.signals:
            print("\nRecent Signals:")
            for sig in list(self.signals)[-3:]:
                time_str = sig['time'].strftime('%H:%M:%S')
                signal_preview = sig['signal'][:60] + "..." if len(sig['signal']) > 60 else sig['signal']
                print(f"  {time_str} - {signal_preview}")
        
        # Error Monitoring
        print("\nERROR MONITORING:")
        print("-" * 40)
        recent_errors = [e for e in self.errors if (datetime.now() - e['time']).seconds < 300]
        if recent_errors:
            print(f"⚠️  {len(recent_errors)} errors in last 5 minutes")
            for err in recent_errors[-3:]:
                print(f"  {err['time'].strftime('%H:%M:%S')} - {err['error'][:60]}...")
        else:
            print("✅ No recent errors")
        
        # Performance
        print("\nPERFORMANCE:")
        print("-" * 40)
        if self.trade_count > 0:
            runtime_hours = (time.time() - self.start_time) / 3600
            trades_per_hour = self.trade_count / max(0.1, runtime_hours)
            print(f"Trades per hour: {trades_per_hour:.1f}")
        else:
            print("No trades executed yet")
        
        print("\n" + "="*60)
        print("Monitor refreshes every 3 seconds")
    
    def format_uptime(self):
        """Format uptime as readable string"""
        uptime = int(time.time() - self.start_time)
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


async def main():
    """Main entry point"""
    monitor = SimpleTradingMonitor()
    await monitor.monitor_trading()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")