#!/usr/bin/env python3
"""
2025 DIAGNOSTIC AND OPTIMIZATION SCRIPT
Latest enhancements based on 2025 market research
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def setup_logging():
    """Setup logging for diagnostics"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(current_dir / "2025_diagnostic.log")
        ]
    )
    return logging.getLogger("2025_Diagnostic")

logger = setup_logging()

class Bot2025Optimizer:
    """Apply latest 2025 optimizations based on research"""
    
    def __init__(self):
        self.config_path = current_dir / "config.json"
        self.src_path = current_dir / "src"
        
    async def run_diagnostic(self):
        """Run comprehensive diagnostic"""
        logger.info("🔍 RUNNING 2025 TRADING BOT DIAGNOSTIC")
        logger.info("=" * 60)
        
        # Check 1: Configuration Analysis
        await self._check_configuration()
        
        # Check 2: 2025 Feature Compliance
        await self._check_2025_features()
        
        # Check 3: API Integration Status
        await self._check_api_integration()
        
        # Check 4: Performance Optimizations
        await self._check_performance_optimizations()
        
        # Check 5: Apply 2025 Updates
        await self._apply_2025_updates()
        
        logger.info("=" * 60)
        logger.info("✅ 2025 DIAGNOSTIC COMPLETE")
        
    async def _check_configuration(self):
        """Check configuration for 2025 compliance"""
        logger.info("📋 Checking Configuration...")
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Check critical 2025 features
            checks = {
                "kraken.use_official_sdk": config.get("kraken", {}).get("use_official_sdk", False),
                "websocket_2025_config": "websocket_2025_config" in config,
                "rate_limiting_v2.enabled": config.get("rate_limiting_v2", {}).get("enabled", False),
                "micro_scalping_engine.enabled": config.get("micro_scalping_engine", {}).get("enabled", False),
                "ai_learning_enabled": config.get("ai_learning_enabled", False),
                "portfolio_intelligence.enabled": config.get("portfolio_intelligence", {}).get("enabled", False),
                "ultra_aggressive_mode": config.get("ultra_aggressive_mode", False),
                "fee_free_optimization": config.get("fee_free_optimization", False)
            }
            
            for feature, enabled in checks.items():
                status = "✅ ENABLED" if enabled else "⚠️  DISABLED"
                logger.info(f"  {feature}: {status}")
            
            # Check API tier
            api_tier = config.get("kraken_api_tier", "starter")
            tier_status = "✅ OPTIMIZED" if api_tier == "starter" else "📈 UPGRADE AVAILABLE"
            logger.info(f"  API Tier: {api_tier} ({tier_status})")
            
            # Check position sizing
            position_size = config.get("position_size_usdt", 0)
            tier_1_limit = config.get("tier_1_trade_limit", 0)
            sizing_status = "✅ TIER-1 OPTIMIZED" if position_size <= 2.0 else "⚠️  MAY EXCEED TIER-1 LIMITS"
            logger.info(f"  Position Size: ${position_size:.2f} ({sizing_status})")
            
        except Exception as e:
            logger.error(f"❌ Configuration check failed: {e}")
    
    async def _check_2025_features(self):
        """Check 2025 feature implementation status"""
        logger.info("🚀 Checking 2025 Features...")
        
        feature_files = {
            "Enhanced Balance Manager": "src/trading/enhanced_balance_manager.py",
            "Infinity Trading Manager": "src/trading/infinity_trading_manager.py", 
            "Universal Learning Manager": "src/learning/universal_learning_manager.py",
            "Circuit Breaker 2025": "src/utils/enhanced_circuit_breaker.py",
            "WebSocket V2 Manager": "src/exchange/websocket_manager_v2.py",
            "Native Kraken Exchange": "src/exchange/native_kraken_exchange.py",
            "Portfolio Tracker": "src/trading/portfolio_tracker.py",
            "Opportunity Scanner": "src/trading/opportunity_scanner.py"
        }
        
        for feature, file_path in feature_files.items():
            full_path = current_dir / file_path
            status = "✅ IMPLEMENTED" if full_path.exists() else "❌ MISSING"
            logger.info(f"  {feature}: {status}")
            
            if full_path.exists():
                # Check file size as proxy for implementation completeness
                size_kb = full_path.stat().st_size / 1024
                complexity = "🧠 ADVANCED" if size_kb > 20 else "📝 BASIC" if size_kb > 5 else "🔍 MINIMAL"
                logger.info(f"    Size: {size_kb:.1f}KB ({complexity})")
    
    async def _check_api_integration(self):
        """Check API integration and credentials"""
        logger.info("🔑 Checking API Integration...")
        
        # Check environment variables
        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET', '')
        
        key_status = "✅ SET" if len(api_key) > 10 else "❌ MISSING"
        secret_status = "✅ SET" if len(api_secret) > 10 else "❌ MISSING"
        
        logger.info(f"  API Key: {key_status} ({len(api_key)} chars)")
        logger.info(f"  API Secret: {secret_status} ({len(api_secret)} chars)")
        
        if api_key and api_secret:
            logger.info(f"  Key Preview: {api_key[:8]}...")
            
        # Check .env file
        env_file = current_dir / ".env"
        env_status = "✅ EXISTS" if env_file.exists() else "❌ MISSING"
        logger.info(f"  .env File: {env_status}")
    
    async def _check_performance_optimizations(self):
        """Check performance optimization status"""
        logger.info("⚡ Checking Performance Optimizations...")
        
        # Check requirements.txt for latest versions
        req_file = current_dir / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                requirements = f.read()
            
            # Key packages and their 2025 recommended versions
            key_packages = {
                "python-kraken-sdk": "3.2.2",
                "ccxt": "4.0",
                "pandas": "2.0",
                "numpy": "1.26",
                "asyncio": "built-in"
            }
            
            for package, recommended in key_packages.items():
                if package in requirements:
                    logger.info(f"  ✅ {package}: Found")
                else:
                    logger.info(f"  ⚠️  {package}: Not found (recommended: {recommended})")
        else:
            logger.info("  ❌ requirements.txt not found")
        
        # Check data directories
        data_dirs = ["D:/trading_data", "D:/trading_bot_logs", "./logs"]
        for data_dir in data_dirs:
            path = Path(data_dir)
            status = "✅ EXISTS" if path.exists() else "📁 CREATE RECOMMENDED"
            logger.info(f"  Data Dir {data_dir}: {status}")
    
    async def _apply_2025_updates(self):
        """Apply latest 2025 optimizations"""
        logger.info("🔧 Applying 2025 Updates...")
        
        updates_applied = []
        
        # Update 1: Enhanced rate limiting for 2025
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Apply 2025 rate limiting optimizations
            if not config.get("rate_limiting_v2", {}).get("micro_scalping_optimized"):
                config.setdefault("rate_limiting_v2", {})["micro_scalping_optimized"] = True
                config.setdefault("rate_limiting_v2", {})["cloudflare_aware"] = True
                config.setdefault("rate_limiting_v2", {})["max_connections_per_ip"] = 140  # Under 150 limit
                updates_applied.append("Enhanced rate limiting for 2025")
            
            # Apply 2025 WebSocket optimizations
            if not config.get("websocket_2025_config", {}).get("connection_rate_limit", {}).get("enabled"):
                config.setdefault("websocket_2025_config", {}).setdefault("connection_rate_limit", {})["enabled"] = True
                config.setdefault("websocket_2025_config", {}).setdefault("connection_rate_limit", {})["max_attempts_per_window"] = 140
                updates_applied.append("WebSocket 2025 connection limits")
            
            # Apply micro-scalping engine 2025 updates
            if not config.get("micro_scalping_engine", {}).get("sub_second_targets"):
                config.setdefault("micro_scalping_engine", {})["sub_second_targets"] = True
                config.setdefault("micro_scalping_engine", {})["latency_target_ms"] = 50
                config.setdefault("micro_scalping_engine", {})["execution_priority"] = "lightning"
                updates_applied.append("Sub-second micro-scalping targets")
            
            # Apply 2025 confidence scoring format
            if config.get("signal_confidence_format") != "decimal":
                config["signal_confidence_format"] = "decimal"
                config.setdefault("advanced_strategy_params", {}).setdefault("confidence_thresholds", {})["ai_enhanced"] = True
                updates_applied.append("2025 confidence scoring format")
            
            # Apply market regime detection 2025
            if not config.get("market_regime_detection_2025"):
                config["market_regime_detection_2025"] = {
                    "enabled": True,
                    "detection_algorithm": "ai_driven",
                    "regime_types": ["bull", "bear", "range", "volatile", "breakout", "low_vol"],
                    "confidence_scoring": True,
                    "real_time_adaptation": True
                }
                updates_applied.append("Market regime detection 2025")
            
            # Save updated configuration
            if updates_applied:
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                for update in updates_applied:
                    logger.info(f"  ✅ Applied: {update}")
            else:
                logger.info("  ✅ All 2025 optimizations already applied")
                
        except Exception as e:
            logger.error(f"  ❌ Error applying updates: {e}")
        
        # Update 2: Create 2025 startup script
        try:
            startup_script = current_dir / "START_BOT_2025_OPTIMIZED.bat"
            startup_content = '''@echo off
echo 🚀 STARTING KRAKEN TRADING BOT - 2025 OPTIMIZED EDITION
echo ============================================================

REM Check if virtual environment exists
if exist "venv\\Scripts\\activate.bat" (
    echo ✅ Activating virtual environment...
    call venv\\Scripts\\activate.bat
) else (
    echo ⚠️  No virtual environment found, using system Python
)

REM Set environment variables for 2025 optimization
set PYTHONPATH=%cd%;%cd%\\src
set KRAKEN_OPTIMIZATION_2025=true
set TRADING_MODE=live
set LOG_LEVEL=INFO

echo ✅ Environment configured for 2025 trading
echo ✅ Python path: %PYTHONPATH%
echo ✅ Starting bot with ultra-low latency mode...

REM Start the bot with 2025 optimizations
python src\\core\\bot.py

echo.
echo Bot execution completed. Press any key to exit...
pause >nul
'''
            
            with open(startup_script, 'w') as f:
                f.write(startup_content)
            
            logger.info("  ✅ Created 2025 optimized startup script")
            updates_applied.append("2025 startup script")
            
        except Exception as e:
            logger.error(f"  ❌ Error creating startup script: {e}")
        
        # Update 3: Create 2025 requirements update
        try:
            req_2025 = current_dir / "requirements_2025_update.txt"
            req_content = '''# 2025 OPTIMIZED REQUIREMENTS
# Latest versions for maximum performance and compatibility

# Core trading
python-kraken-sdk==3.2.2
ccxt>=4.0.0

# Data processing (2025 optimized)
pandas>=2.0.0
numpy==1.26.4
scipy>=1.11.0

# Async and networking
aiohttp>=3.8.0
websockets>=11.0.0
asyncio-mqtt>=0.13.0

# Technical analysis
ta-lib>=0.4.26
pandas-ta>=0.3.14b0

# Performance monitoring
psutil>=5.9.0
memory-profiler>=0.60.0

# Logging and utilities
python-dotenv>=1.0.0
colorlog>=6.7.0
click>=8.1.0

# Optional AI/ML (if using learning features)
scikit-learn>=1.3.0
tensorflow>=2.13.0

# Development tools
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
'''
            
            with open(req_2025, 'w') as f:
                f.write(req_content)
            
            logger.info("  ✅ Created 2025 requirements update file")
            updates_applied.append("2025 requirements file")
            
        except Exception as e:
            logger.error(f"  ❌ Error creating requirements: {e}")
        
        logger.info(f"📊 Total updates applied: {len(updates_applied)}")
        
        return updates_applied

async def main():
    """Main diagnostic function"""
    print("🤖 KRAKEN TRADING BOT - 2025 DIAGNOSTIC & OPTIMIZATION")
    print("=" * 70)
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Working Directory: {Path.cwd()}")
    print("=" * 70)
    
    optimizer = Bot2025Optimizer()
    await optimizer.run_diagnostic()
    
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDATIONS:")
    print("1. If all checks passed ✅, your bot is 2025-ready!")
    print("2. Run: START_BOT_2025_OPTIMIZED.bat to launch")
    print("3. Monitor logs for any API key or connection issues")
    print("4. Consider upgrading to Kraken Pro tier for higher limits")
    print("5. Update requirements: pip install -r requirements_2025_update.txt")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
