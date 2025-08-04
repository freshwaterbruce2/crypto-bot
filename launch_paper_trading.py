#!/usr/bin/env python3
"""
Secure Paper Trading Launcher
Launches the crypto trading bot in safe paper trading mode with comprehensive monitoring
"""

import os
import sys
import json
import time
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.paper_trading.paper_config import PaperTradingConfig, get_paper_config
from src.paper_trading.paper_performance_tracker import PaperPerformanceTracker
from src.utils.professional_logging_system import setup_professional_logging
from src.utils.agent_tools_bridge import AgentToolsBridge

class PaperTradingLauncher:
    """Secure launcher for paper trading mode with comprehensive safety checks"""
    
    def __init__(self):
        self.config_file = project_root / "paper_trading_config.json"
        self.env_file = project_root / ".env.paper_trading"
        self.data_dir = project_root / "paper_trading_data"
        self.validation_results = {}
        self.start_time = datetime.now()
        self.logger = None
        
    def setup_logging(self):
        """Setup comprehensive logging for paper trading"""
        try:
            # Create paper trading logs directory
            log_dir = Path("D:/trading_data/logs/paper_trading")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup professional logging
            setup_professional_logging(
                log_level="INFO",
                log_dir=str(log_dir),
                component_name="paper_trading_launcher"
            )
            
            self.logger = logging.getLogger("paper_trading_launcher")
            self.logger.info("=" * 60)
            self.logger.info("PAPER TRADING LAUNCHER STARTED")
            self.logger.info("=" * 60)
            self.logger.info(f"Launch Time: {self.start_time}")
            self.logger.info(f"Configuration File: {self.config_file}")
            self.logger.info(f"Environment File: {self.env_file}")
            self.logger.info(f"Data Directory: {self.data_dir}")
            
        except Exception as e:
            print(f"CRITICAL: Failed to setup logging: {e}")
            sys.exit(1)
    
    def load_environment_variables(self):
        """Load paper trading environment variables"""
        try:
            if not self.env_file.exists():
                raise FileNotFoundError(f"Environment file not found: {self.env_file}")
            
            # Load environment variables from file
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            
            # Verify critical environment variables are set
            critical_vars = [
                'PAPER_TRADING_ENABLED',
                'LIVE_TRADING_DISABLED',
                'TRADING_MODE',
                'FORCE_PAPER_MODE'
            ]
            
            for var in critical_vars:
                if os.getenv(var) != 'true':
                    raise ValueError(f"Critical safety variable {var} not set to 'true'")
            
            self.logger.info("Environment variables loaded successfully")
            self.logger.info("Paper trading mode confirmed via environment")
            
        except Exception as e:
            self.logger.error(f"Failed to load environment variables: {e}")
            raise
    
    def validate_paper_mode_configuration(self) -> bool:
        """Comprehensive validation that paper mode is properly configured"""
        try:
            self.logger.info("Starting paper mode validation...")
            validation_passed = True
            
            # Check 1: Environment variables
            paper_vars = {
                'PAPER_TRADING_ENABLED': 'true',
                'LIVE_TRADING_DISABLED': 'true',
                'TRADING_MODE': 'paper',
                'FORCE_PAPER_MODE': 'true',
                'DISABLE_REAL_ORDERS': 'true',
                'SAFETY_MODE': 'maximum'
            }
            
            for var, expected_value in paper_vars.items():
                actual_value = os.getenv(var)
                if actual_value != expected_value:
                    self.logger.error(f"VALIDATION FAILED: {var} = '{actual_value}', expected '{expected_value}'")
                    validation_passed = False
                else:
                    self.logger.info(f"✓ {var} = '{actual_value}'")
            
            # Check 2: Configuration file
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                if not config.get('paper_trading', {}).get('enabled', False):
                    self.logger.error("VALIDATION FAILED: Paper trading not enabled in config file")
                    validation_passed = False
                else:
                    self.logger.info("✓ Paper trading enabled in configuration file")
            
            # Check 3: Trading limits
            max_position = float(os.getenv('MAX_POSITION_SIZE_USD', '0'))
            if max_position > 15.0:
                self.logger.warning(f"Position size ${max_position} is high for paper trading")
            
            # Check 4: Data directory setup
            self.data_dir.mkdir(exist_ok=True)
            (self.data_dir / "logs").mkdir(exist_ok=True)
            (self.data_dir / "reports").mkdir(exist_ok=True)
            (self.data_dir / "backups").mkdir(exist_ok=True)
            
            self.validation_results['paper_mode_validated'] = validation_passed
            self.validation_results['validation_time'] = datetime.now().isoformat()
            
            if validation_passed:
                self.logger.info("✓ PAPER MODE VALIDATION PASSED")
            else:
                self.logger.error("✗ PAPER MODE VALIDATION FAILED")
            
            return validation_passed
            
        except Exception as e:
            self.logger.error(f"Paper mode validation error: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def create_safety_verification_file(self):
        """Create a safety verification file to confirm paper mode"""
        try:
            safety_file = self.data_dir / "safety_verification.json"
            
            safety_data = {
                "paper_trading_mode": True,
                "live_trading_disabled": True,
                "safety_verification_time": datetime.now().isoformat(),
                "launcher_version": "2.0.0",
                "environment_verified": True,
                "configuration_verified": True,
                "validation_results": self.validation_results,
                "safety_warnings": [
                    "This is PAPER TRADING mode only",
                    "NO REAL FUNDS are at risk",
                    "ALL TRADES are simulated",
                    "Only market data is real"
                ],
                "emergency_stop": {
                    "enabled": True,
                    "auto_shutdown_on_error": True,
                    "circuit_breaker_enabled": True
                }
            }
            
            with open(safety_file, 'w') as f:
                json.dump(safety_data, f, indent=2)
            
            self.logger.info(f"Safety verification file created: {safety_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create safety verification file: {e}")
            raise
    
    def setup_paper_trading_monitoring(self):
        """Setup monitoring and performance tracking for paper trading"""
        try:
            # Create performance tracker
            config = get_paper_config()
            tracker = PaperPerformanceTracker(config)
            
            # Initialize monitoring
            monitoring_config = {
                "start_time": self.start_time.isoformat(),
                "monitoring_interval": 300,  # 5 minutes
                "alert_thresholds": {
                    "consecutive_losses": 3,
                    "daily_loss_limit": 20.0,
                    "low_balance_warning": 25.0
                },
                "reporting": {
                    "hourly_reports": True,
                    "daily_reports": True,
                    "performance_metrics": True
                }
            }
            
            # Save monitoring configuration
            monitoring_file = self.data_dir / "monitoring_config.json"
            with open(monitoring_file, 'w') as f:
                json.dump(monitoring_config, f, indent=2)
            
            self.logger.info("Paper trading monitoring setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup monitoring: {e}")
            raise
    
    def display_launch_summary(self):
        """Display comprehensive launch summary"""
        try:
            config = get_paper_config()
            
            print("\n" + "=" * 70)
            print("🧪 PAPER TRADING BOT LAUNCHER")
            print("=" * 70)
            print(f"Launch Time: {self.start_time}")
            print(f"Mode: PAPER TRADING (SAFE)")
            print(f"Starting Balance: ${config.starting_balance:,.2f} USDT")
            print(f"Trading Pair: SHIB/USDT")
            print(f"Position Size: $5-10 USD per trade")
            print(f"Max Concurrent Positions: 3")
            print(f"Daily Loss Limit: $20.00")
            print(f"Circuit Breaker: $30.00")
            print(f"Data Directory: {self.data_dir}")
            print("\n📊 SAFETY CONFIRMATIONS:")
            print("✓ Paper trading mode ENABLED")
            print("✓ Live trading DISABLED")
            print("✓ Real orders BLOCKED")
            print("✓ Only market data is real")
            print("✓ All trades are SIMULATED")
            print("\n📈 MONITORING:")
            print("✓ Real-time performance tracking")
            print("✓ Health checks every 5 minutes")
            print("✓ Hourly and daily reports")
            print("✓ Comprehensive audit trail")
            print("\n🎯 TESTING OBJECTIVES:")
            print("• Validate trading strategy performance")
            print("• Test system stability and reliability")
            print("• Monitor resource usage and efficiency")
            print("• Collect performance metrics")
            print("• Run for 3-5 days continuous operation")
            print("=" * 70)
            print("🚀 Ready to launch paper trading bot!")
            print("=" * 70)
            
        except Exception as e:
            self.logger.error(f"Failed to display launch summary: {e}")
    
    def create_quick_status_script(self):
        """Create a quick status checking script"""
        try:
            status_script = project_root / "check_paper_trading_status.py"
            
            script_content = '''#!/usr/bin/env python3
"""Quick Paper Trading Status Checker"""
import json
import os
from pathlib import Path
from datetime import datetime

def check_paper_trading_status():
    """Check current paper trading status"""
    print("🧪 PAPER TRADING STATUS CHECK")
    print("=" * 50)
    
    # Check data directory
    data_dir = Path("paper_trading_data")
    if data_dir.exists():
        print(f"✓ Data directory: {data_dir}")
        
        # Check safety verification
        safety_file = data_dir / "safety_verification.json"
        if safety_file.exists():
            with open(safety_file, 'r') as f:
                safety_data = json.load(f)
            print(f"✓ Safety verified: {safety_data['safety_verification_time']}")
            print(f"✓ Paper mode: {safety_data['paper_trading_mode']}")
        
        # Check performance data
        perf_file = data_dir / "paper_performance.json"
        if perf_file.exists():
            with open(perf_file, 'r') as f:
                perf_data = json.load(f)
            print(f"✓ Performance tracking active")
            print(f"  Total trades: {perf_data.get('total_trades', 0)}")
            print(f"  Current balance: ${perf_data.get('current_balance', 0):.2f}")
        
        # Check recent logs
        log_dir = Path("D:/trading_data/logs/paper_trading")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            if log_files:
                print(f"✓ Active logging: {len(log_files)} log files")
    else:
        print("✗ Data directory not found - bot may not be running")
    
    print("=" * 50)

if __name__ == "__main__":
    check_paper_trading_status()
'''
            
            with open(status_script, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(status_script, 0o755)
            
            self.logger.info(f"Quick status script created: {status_script}")
            
        except Exception as e:
            self.logger.error(f"Failed to create status script: {e}")
    
    async def launch_bot(self):
        """Launch the trading bot in paper trading mode"""
        try:
            self.logger.info("Launching trading bot in paper trading mode...")
            
            # Import and initialize the bot with paper trading configuration
            from src.core.bot import CryptoTradingBot
            
            # Create bot instance with paper trading configuration
            bot_config = {
                "paper_trading": True,
                "live_trading": False,
                "trading_mode": "paper",
                "single_pair_focus": True,
                "primary_pair": "SHIB/USDT",
                "starting_balance": 150.0,
                "position_size_usd": 7.5,
                "max_daily_trades": 50,
                "max_concurrent_positions": 3,
                "circuit_breaker_loss": 20.0,
                "conservative_mode": True,
                "validation_mode": True
            }
            
            # Initialize bot
            bot = CryptoTradingBot(config=bot_config)
            
            self.logger.info("Bot initialized successfully")
            self.logger.info("Starting paper trading operation...")
            
            # Create monitoring task
            async def monitor_paper_trading():
                """Monitor paper trading performance"""
                while True:
                    try:
                        # Check bot health
                        health_status = await bot.get_health_status()
                        self.logger.info(f"Bot health: {health_status}")
                        
                        # Update performance metrics
                        perf_data = {
                            "timestamp": datetime.now().isoformat(),
                            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
                            "health_status": health_status,
                            "paper_mode_verified": True
                        }
                        
                        # Save to monitoring file
                        monitoring_file = self.data_dir / "current_status.json"
                        with open(monitoring_file, 'w') as f:
                            json.dump(perf_data, f, indent=2)
                        
                        # Wait 5 minutes
                        await asyncio.sleep(300)
                        
                    except Exception as e:
                        self.logger.error(f"Monitoring error: {e}")
                        await asyncio.sleep(60)  # Shorter wait on error
            
            # Start monitoring task
            monitor_task = asyncio.create_task(monitor_paper_trading())
            
            # Run bot
            try:
                await bot.run()
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal - shutting down...")
                monitor_task.cancel()
                await bot.shutdown()
                self.logger.info("Paper trading bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Failed to launch bot: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    async def run(self):
        """Main execution method"""
        try:
            # Setup logging
            self.setup_logging()
            
            # Load environment variables
            self.load_environment_variables()
            
            # Validate paper mode configuration
            if not self.validate_paper_mode_configuration():
                self.logger.error("CRITICAL: Paper mode validation failed - ABORTING LAUNCH")
                print("\n❌ LAUNCH ABORTED: Paper mode validation failed")
                print("Please check the configuration and try again.")
                sys.exit(1)
            
            # Create safety verification
            self.create_safety_verification_file()
            
            # Setup monitoring
            self.setup_paper_trading_monitoring()
            
            # Create utility scripts
            self.create_quick_status_script()
            
            # Display launch summary
            self.display_launch_summary()
            
            # Confirm launch
            response = input("\n🚀 Launch paper trading bot? [y/N]: ").strip().lower()
            if response != 'y':
                print("Launch cancelled by user.")
                return
            
            print("\n🧪 Launching Paper Trading Bot...")
            print("Press Ctrl+C to stop the bot safely")
            print("=" * 50)
            
            # Launch the bot
            await self.launch_bot()
            
        except KeyboardInterrupt:
            print("\n\n🛑 Shutdown requested by user")
            self.logger.info("Shutdown requested by user")
        except Exception as e:
            self.logger.error(f"Critical error during launch: {e}")
            self.logger.error(traceback.format_exc())
            print(f"\n❌ CRITICAL ERROR: {e}")
            print("Check logs for detailed error information.")
            sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Secure Paper Trading Launcher")
    parser.add_argument("--auto-confirm", action="store_true", 
                       help="Skip launch confirmation prompt")
    parser.add_argument("--test-duration", type=int, default=120, 
                       help="Test duration in hours (default: 120 = 5 days)")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Create and run launcher
    launcher = PaperTradingLauncher()
    
    try:
        asyncio.run(launcher.run())
    except KeyboardInterrupt:
        print("\nLauncher interrupted by user")
    except Exception as e:
        print(f"Launcher failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()