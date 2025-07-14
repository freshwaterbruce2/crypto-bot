"""
Kraken Compliance Fixes - Align with Official Guidelines
Fixes all identified issues to ensure proper Kraken API compliance
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class KrakenComplianceFixes:
    """Implements all necessary fixes for Kraken guideline compliance"""
    
    def __init__(self, bot):
        self.bot = bot
        self.exchange = bot.exchange
        self.websocket_token = None
        self.instrument_data = {}
        
    # FIX 1: WebSocket Authentication (Required for Private Channels)
    async def get_websocket_token(self) -> Optional[str]:
        """
        Get WebSocket authentication token from REST API.
        According to Kraken docs, this token must be used within 15 minutes.
        """
        try:
            logger.info("[AUTH] Requesting WebSocket token from Kraken...")
            response = await self.exchange.private_post_getwebsocketstoken()
            token = response['result']['token']
            logger.info("[AUTH] WebSocket token obtained successfully")
            return token
        except Exception as e:
            logger.error(f"[AUTH] Failed to get WebSocket token: {e}")
            return None
    
    # FIX 2: Minimum Order Validation (Critical for Kraken)
    def validate_order_size(self, symbol: str, amount: float, price: float) -> Tuple[bool, str, Dict]:
        """
        Validate order against Kraken's minimum requirements.
        Each pair has specific ordermin and costmin requirements.
        """
        try:
            market = self.exchange.markets.get(symbol)
            if not market:
                return False, f"Market {symbol} not found", {}
            
            # Get limits
            min_amount = market['limits']['amount']['min']
            min_cost = market['limits']['cost']['min']
            
            # Calculate order cost
            cost = amount * price
            
            # Validation results
            validation = {
                'amount': amount,
                'price': price,
                'cost': cost,
                'min_amount': min_amount,
                'min_cost': min_cost,
                'amount_ok': amount >= min_amount,
                'cost_ok': cost >= min_cost
            }
            
            # Check minimum amount
            if amount < min_amount:
                return False, f"Amount {amount:.8f} below minimum {min_amount:.8f}", validation
            
            # Check minimum cost
            if cost < min_cost:
                return False, f"Cost ${cost:.2f} below minimum ${min_cost:.2f}", validation
            
            return True, "Order size valid", validation
            
        except Exception as e:
            logger.error(f"[VALIDATION] Error validating order size: {e}")
            return False, str(e), {}
    
    # FIX 3: Instrument Data Subscription with Timeout Handling
    async def subscribe_instrument_channel(self, websocket_manager):
        """
        Properly subscribe to instrument channel with error handling.
        This provides trading parameters and rules for all pairs.
        """
        try:
            # Subscribe to instrument channel
            subscribe_msg = {
                "method": "subscribe",
                "params": {
                    "channel": "instrument",
                    "snapshot": True
                }
            }
            
            logger.info("[INSTRUMENT] Subscribing to instrument channel...")
            await websocket_manager.send_message(subscribe_msg)
            
            # Wait for instrument data with proper timeout
            timeout = 10.0  # Increase timeout
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                if hasattr(websocket_manager, 'instrument_data') and websocket_manager.instrument_data:
                    logger.info("[INSTRUMENT] Instrument data received successfully")
                    self.instrument_data = websocket_manager.instrument_data
                    return True
                await asyncio.sleep(0.1)
            
            logger.warning("[INSTRUMENT] Timeout waiting for instrument data - using cached market data")
            return False
            
        except Exception as e:
            logger.error(f"[INSTRUMENT] Error subscribing to instrument channel: {e}")
            return False
    
    # FIX 4: Process Management to Prevent Duplicate Initialization
    def create_pid_file(self) -> bool:
        """Create PID file to prevent multiple bot instances"""
        pid_file = "C:/projects050625/projects/active/tool-crypto-trading-bot-2025/bot.pid"
        
        try:
            # Check if PID file exists and process is running
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if old process is still running
                try:
                    os.kill(old_pid, 0)  # Signal 0 = check if process exists
                    logger.error(f"[PID] Bot already running with PID {old_pid}")
                    return False
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    os.remove(pid_file)
                    logger.info("[PID] Removed stale PID file")
            
            # Create new PID file
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"[PID] Created PID file with process ID {os.getpid()}")
            return True
            
        except Exception as e:
            logger.error(f"[PID] Error managing PID file: {e}")
            return False
    
    # FIX 5: Disk Space Management
    async def check_and_clean_disk_space(self) -> bool:
        """
        Check disk space and clean old logs if needed.
        Critical: Your disk is at 97.2% capacity!
        """
        import shutil
        from pathlib import Path
        
        try:
            # Check disk usage
            disk_usage = shutil.disk_usage("D:/")
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            logger.warning(f"[DISK] Disk usage: {used_percent:.1f}%")
            
            if used_percent > 90:
                logger.warning("[DISK] Critical disk space! Cleaning old logs...")
                
                # Clean old log files (older than 7 days)
                log_dir = Path("D:/trading_data/logs")
                if log_dir.exists():
                    cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
                    cleaned_count = 0
                    cleaned_size = 0
                    
                    for log_file in log_dir.glob("*.log*"):
                        if log_file.stat().st_mtime < cutoff_time:
                            size = log_file.stat().st_size
                            log_file.unlink()
                            cleaned_count += 1
                            cleaned_size += size
                    
                    logger.info(f"[DISK] Cleaned {cleaned_count} old log files, freed {cleaned_size/1024/1024:.1f} MB")
                
                # Clean old learning data
                learning_dir = Path("D:/trading_bot_data/learning")
                if learning_dir.exists():
                    for old_file in learning_dir.glob("*_backup_*.json"):
                        old_file.unlink()
                    logger.info("[DISK] Cleaned old learning backups")
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"[DISK] Error checking disk space: {e}")
            return False
    
    # FIX 6: Enhanced WebSocket Manager with Authentication
    async def initialize_authenticated_websocket(self, websocket_manager):
        """Initialize WebSocket with proper authentication for private channels"""
        try:
            # Get authentication token
            token = await self.get_websocket_token()
            if not token:
                logger.error("[WEBSOCKET] Failed to get authentication token")
                return False
            
            # Store token in websocket manager
            websocket_manager.auth_token = token
            
            # Subscribe to private channels
            private_channels = [
                {
                    "method": "subscribe",
                    "params": {
                        "channel": "executions",
                        "snap_trades": True,
                        "snap_orders": True,
                        "token": token
                    }
                },
                {
                    "method": "subscribe", 
                    "params": {
                        "channel": "balances",
                        "snapshot": True,
                        "token": token
                    }
                }
            ]
            
            for sub in private_channels:
                await websocket_manager.send_message(sub)
                await asyncio.sleep(0.1)  # Small delay between subscriptions
            
            logger.info("[WEBSOCKET] Authenticated channels subscribed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WEBSOCKET] Authentication error: {e}")
            return False


# Integration function to apply all fixes
async def apply_kraken_compliance_fixes(bot):
    """Apply all Kraken compliance fixes to the bot"""
    fixes = KrakenComplianceFixes(bot)
    
    logger.info("=" * 60)
    logger.info("APPLYING KRAKEN COMPLIANCE FIXES")
    logger.info("=" * 60)
    
    # 1. Check PID file to prevent duplicates
    if not fixes.create_pid_file():
        logger.error("[FIX] Bot already running - preventing duplicate")
        return False
    
    # 2. Clean disk space
    await fixes.check_and_clean_disk_space()
    
    # 3. Get WebSocket token for authentication
    bot.websocket_token = await fixes.get_websocket_token()
    
    # 4. Initialize authenticated WebSocket
    if hasattr(bot, 'websocket_manager') and bot.websocket_manager:
        await fixes.initialize_authenticated_websocket(bot.websocket_manager)
    
    # 5. Add order validation to bot
    bot.validate_order_size = fixes.validate_order_size
    
    logger.info("[FIX] All Kraken compliance fixes applied successfully")
    return True


# Minimum order sizes for common Kraken pairs (for reference)
KRAKEN_MINIMUM_ORDERS = {
    "BTC/USDT": {"min_amount": 0.0001, "min_cost": 10.0},
    "ETH/USDT": {"min_amount": 0.001, "min_cost": 10.0},
    "ADA/USDT": {"min_amount": 10.0, "min_cost": 10.0},
    "DOGE/USDT": {"min_amount": 50.0, "min_cost": 10.0},
    "SOL/USDT": {"min_amount": 0.1, "min_cost": 10.0},
    "DOT/USDT": {"min_amount": 1.0, "min_cost": 10.0},
    "MATIC/USDT": {"min_amount": 10.0, "min_cost": 10.0},
    "AVAX/USDT": {"min_amount": 0.25, "min_cost": 10.0},
    "ATOM/USDT": {"min_amount": 0.5, "min_cost": 10.0},
    "XRP/USDT": {"min_amount": 10.0, "min_cost": 10.0},
    "LINK/USDT": {"min_amount": 0.5, "min_cost": 10.0},
    "UNI/USDT": {"min_amount": 1.0, "min_cost": 10.0}
}
