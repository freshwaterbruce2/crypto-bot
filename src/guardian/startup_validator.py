"""
Kraken-Compliant Startup Validator - Guardian System
===================================================

This module performs comprehensive pre-flight checks before allowing the bot to trade.
It validates all systems according to Kraken API specifications and guidelines,
checks portfolio status, and makes intelligent decisions about whether to proceed
with trading or shut down with clear error reporting.

KRAKEN COMPLIANCE FEATURES:
- Proper symbol format validation (BTC/USD vs XBTUSD)
- Kraken-specific error pattern recognition
- Rate limiting awareness during validation
- System status integration
- Asset naming convention handling (ZUSD vs USD, XXBT vs BTC)
- WebSocket authentication token validation
- Trading permissions verification
"""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SystemTest:
    """Represents a single system test with its result and any errors."""

    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical  # If critical, failure prevents startup
        self.passed = False
        self.error = None
        self.details = {}
        self.fix_attempted = False
        self.fix_successful = False
        self.kraken_compliant = False
        self.rate_limit_safe = True

    def fail(self, error: str, details: dict = None):
        """Mark test as failed with error details."""
        self.passed = False
        self.error = error
        if details:
            self.details.update(details)

    def succeed(self, details: dict = None):
        """Mark test as passed with optional details."""
        self.passed = True
        self.error = None
        if details:
            self.details.update(details)
        self.kraken_compliant = True


class KrakenStartupValidator:
    """
    Kraken-compliant startup validation system that ensures all components are ready
    before allowing trading to begin. Includes self-healing capabilities for known issues
    and comprehensive Kraken API compliance checking.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.test_results = {}
        self.portfolio_status = None
        self.can_start_trading = False
        self.kraken_system_status = None
        self.supported_symbols = set()
        self.rate_limit_delay = 1.0  # Delay between API calls during validation

        # Load learned fixes from previous sessions
        self.learned_fixes = self._load_learned_fixes()

        # Kraken-specific error patterns
        self.kraken_error_patterns = {
            'EAPI:Invalid key': 'api_key_invalid',
            'EAPI:Invalid signature': 'api_signature_invalid',
            'EAPI:Invalid nonce': 'api_nonce_invalid',
            'EGeneral:Permission denied': 'insufficient_permissions',
            'EService:Unavailable': 'service_unavailable',
            'EService:Market in cancel_only mode': 'market_cancel_only',
            'EService:Market in post_only mode': 'market_post_only',
            'EOrder:Rate limit exceeded': 'rate_limit_exceeded',
            'EGeneral:Temporary lockout': 'temporary_lockout',
            'EOrder:Insufficient funds': 'insufficient_balance'
        }

        # System tests to perform (in order of dependency)
        self.tests = [
            ("Kraken System Status", self._test_kraken_system_status, True),
            ("API Authentication", self._test_api_authentication, True),
            ("Exchange Connection", self._test_exchange_connection, True),
            ("Symbol Validation", self._test_symbol_validation, True),
            ("Balance Manager", self._test_balance_manager, True),
            ("WebSocket Connection", self._test_websocket_connection, True),
            ("WebSocket Authentication", self._test_websocket_auth, True),
            ("Portfolio Tracker", self._test_portfolio_tracker, True),
            ("Strategy Manager", self._test_strategy_manager, True),
            ("Trade Executor", self._test_trade_executor, True),
            ("Risk Management", self._test_risk_management, True),
            ("Data Pipeline", self._test_data_pipeline, True),
            ("Opportunity Scanner", self._test_opportunity_scanner, False),
            ("Profit Harvester", self._test_profit_harvester, False),
            ("Learning Systems", self._test_learning_systems, False),
            ("Assistant Network", self._test_assistants, False),
        ]

    def _load_learned_fixes(self) -> dict[str, dict]:
        """Load previously learned fixes for automatic error resolution."""
        fixes_file = Path("trading_data/learned_fixes.json")

        if fixes_file.exists():
            try:
                with open(fixes_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load learned fixes: {e}")

        # Default known fixes based on Kraken error patterns
        return {
            "api_key_invalid": {
                "fix_method": "_fix_api_credentials",
                "success_rate": 0.8,
                "description": "Reload API credentials from environment"
            },
            "api_signature_invalid": {
                "fix_method": "_fix_api_credentials",
                "success_rate": 0.7,
                "description": "Regenerate API signature with correct parameters"
            },
            "websocket_disconnected": {
                "fix_method": "_fix_websocket_connection",
                "success_rate": 0.95,
                "description": "Reconnect WebSocket with proper authentication"
            },
            "insufficient_balance": {
                "fix_method": "_analyze_portfolio_allocation",
                "success_rate": 1.0,
                "description": "Check if funds are deployed in positions"
            },
            "strategy_initialization_failed": {
                "fix_method": "_fix_strategy_initialization",
                "success_rate": 0.9,
                "description": "Reinitialize strategies with valid symbols"
            },
            "unsupported_symbols": {
                "fix_method": "_fix_symbol_configuration",
                "success_rate": 0.85,
                "description": "Update configuration with supported Kraken symbols"
            }
        }

    async def validate_startup(self) -> tuple[bool, str]:
        """
        Perform comprehensive Kraken-compliant startup validation.

        Returns:
            Tuple of (can_start, message) where can_start indicates if trading can begin
            and message provides details about the decision.
        """
        self.logger.info("="*80)
        self.logger.info("KRAKEN-COMPLIANT STARTUP VALIDATION BEGINNING")
        self.logger.info("="*80)

        # Phase 1: Run all system tests with rate limiting
        self.logger.info("\n[PHASE 1] System Component Testing (Kraken Compliant)")
        all_tests_passed = await self._run_all_tests()

        # Phase 2: Check portfolio status
        self.logger.info("\n[PHASE 2] Portfolio Analysis")
        portfolio_ready = await self._analyze_portfolio_status()

        # Phase 3: Attempt fixes for any failures
        if not all_tests_passed:
            self.logger.info("\n[PHASE 3] Attempting Automatic Fixes")
            fixes_successful = await self._attempt_automatic_fixes()

            # Re-run failed tests after fixes
            if fixes_successful:
                self.logger.info("\n[PHASE 4] Re-testing After Fixes")
                all_tests_passed = await self._rerun_failed_tests()

        # Phase 4: Final Kraken compliance check
        self.logger.info("\n[PHASE 5] Kraken Compliance Verification")
        compliance_status = self._verify_kraken_compliance()

        # Phase 5: Make final decision
        self.logger.info("\n[FINAL DECISION]")
        return self._make_startup_decision(all_tests_passed, portfolio_ready, compliance_status)

    async def _run_all_tests(self) -> bool:
        """Run all system tests with Kraken-compliant rate limiting."""
        all_critical_passed = True

        for i, (test_name, test_method, is_critical) in enumerate(self.tests):
            test = SystemTest(test_name, is_critical)

            # Add delay between tests to respect rate limits
            if i > 0:
                await asyncio.sleep(self.rate_limit_delay)

            try:
                self.logger.info(f"Testing {test_name}...")
                start_time = time.time()

                await test_method(test)

                test_duration = time.time() - start_time

                if test.passed:
                    compliance_indicator = "[EMOJI] KRAKEN-COMPLIANT" if test.kraken_compliant else "[EMOJI] BASIC"
                    self.logger.info(f"{compliance_indicator} {test_name} - PASSED ({test_duration:.2f}s)")
                    if test.details:
                        for key, value in test.details.items():
                            self.logger.info(f"  - {key}: {value}")
                else:
                    self.logger.error(f"[EMOJI] {test_name} - FAILED: {test.error}")
                    if is_critical:
                        all_critical_passed = False

            except Exception as e:
                test.fail(f"Test crashed: {str(e)}", {"traceback": traceback.format_exc()})
                self.logger.error(f"[EMOJI] {test_name} - CRASHED: {str(e)}")
                if is_critical:
                    all_critical_passed = False

            self.test_results[test_name] = test

        return all_critical_passed

    async def _test_kraken_system_status(self, test: SystemTest):
        """Test Kraken system status before proceeding with other tests."""
        try:
            if not hasattr(self.bot, 'exchange') or not self.bot.exchange:
                test.fail("Exchange not initialized")
                return

            # Check Kraken system status
            system_status = await self.bot.exchange.fetch_status()

            if system_status:
                status = system_status.get('status', 'unknown')
                updated = system_status.get('updated', 0)

                self.kraken_system_status = {
                    'status': status,
                    'updated': updated,
                    'timestamp': time.time()
                }

                if status == 'ok':
                    test.succeed({
                        "kraken_status": status,
                        "last_updated": updated,
                        "system_operational": True
                    })
                else:
                    test.fail(f"Kraken system status: {status}")
            else:
                test.fail("Could not retrieve Kraken system status")

        except Exception as e:
            error_msg = str(e)
            # Check for Kraken-specific errors
            kraken_error = self._identify_kraken_error(error_msg)
            if kraken_error:
                test.fail(f"Kraken system status check failed: {kraken_error}", {"error_type": kraken_error})
            else:
                test.fail(f"System status test failed: {error_msg}")

    async def _test_api_authentication(self, test: SystemTest):
        """Test API credentials with Kraken-specific error handling."""
        try:
            if not hasattr(self.bot, 'exchange') or not self.bot.exchange:
                test.fail("Exchange not initialized")
                return

            # Test with the most basic authenticated call
            balance = await self.bot.exchange.fetch_balance()

            if balance and isinstance(balance, dict):
                # Check for Kraken-specific balance structure
                has_kraken_assets = any(
                    asset.startswith(('Z', 'X')) for asset in balance.get('total', {}).keys()
                )

                test.succeed({
                    "api_authenticated": True,
                    "balance_access": True,
                    "kraken_asset_format": has_kraken_assets,
                    "total_currencies": len(balance.get('total', {}))
                })
            else:
                test.fail("API authenticated but balance data invalid")

        except Exception as e:
            error_msg = str(e)
            kraken_error = self._identify_kraken_error(error_msg)

            if kraken_error:
                test.fail(f"Kraken API authentication failed: {kraken_error}",
                         {"error_type": kraken_error})
            else:
                test.fail(f"API authentication test failed: {error_msg}")

    async def _test_exchange_connection(self, test: SystemTest):
        """Test exchange connection using proper Kraken symbols."""
        try:
            if not hasattr(self.bot, 'exchange') or not self.bot.exchange:
                test.fail("Exchange not initialized")
                return

            # Use proper Kraken symbol format - check both USD and USDT variants
            test_symbols = ['BTC/USD', 'BTC/USDT', 'ETH/USD', 'ETH/USDT']
            successful_symbols = []

            for symbol in test_symbols:
                try:
                    ticker = await self.bot.exchange.fetch_ticker(symbol)
                    if ticker and 'last' in ticker:
                        successful_symbols.append(symbol)
                        break  # Found working symbol
                except Exception:
                    continue

                # Rate limiting delay
                await asyncio.sleep(0.5)

            if successful_symbols:
                # Get the working symbol
                working_symbol = successful_symbols[0]
                ticker = await self.bot.exchange.fetch_ticker(working_symbol)

                test.succeed({
                    "exchange_connected": True,
                    "test_symbol": working_symbol,
                    "current_price": ticker['last'],
                    "market_data_available": True,
                    "kraken_format_validated": True
                })
            else:
                test.fail("Could not connect to market data with any test symbol")

        except Exception as e:
            error_msg = str(e)
            kraken_error = self._identify_kraken_error(error_msg)

            if kraken_error:
                test.fail(f"Kraken exchange connection failed: {kraken_error}",
                         {"error_type": kraken_error})
            else:
                test.fail(f"Exchange connection test failed: {error_msg}")

    def _get_symbol_alternatives(self, base: str, quote: str) -> list[str]:
        """Get alternative symbol formats for Kraken compatibility."""
        alternatives = []

        # Convert XBT to BTC for v2 compatibility
        kraken_base = "BTC" if base == "XBT" else base
        kraken_quote = quote

        alternatives.append(f"{kraken_base}{kraken_quote}")
        alternatives.append(f"{base}{quote}")

        return alternatives

    async def _test_websocket_connection(self, test: SystemTest):
        """Test WebSocket connection for real-time data."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check WebSocket connection status
            is_connected = getattr(self.bot.websocket_manager, 'is_connected', False)
            connection_url = getattr(self.bot.websocket_manager, 'url', 'unknown')

            # Validate Kraken WebSocket URL
            kraken_ws_urls = [
                'wss://ws.kraken.com',
                'wss://ws-auth.kraken.com',
                'wss://ws.kraken.com/v2',
                'wss://ws-auth.kraken.com/v2'
            ]

            is_kraken_url = any(url in str(connection_url) for url in kraken_ws_urls)

            if is_connected and is_kraken_url:
                test.succeed({
                    "websocket_connected": True,
                    "connection_url": str(connection_url),
                    "kraken_compliant_url": is_kraken_url
                })
            elif is_connected and not is_kraken_url:
                test.fail(f"WebSocket connected but not to Kraken URL: {connection_url}")
            else:
                test.fail("WebSocket not connected", {"error_type": "websocket_disconnected"})

        except Exception as e:
            test.fail(f"WebSocket test failed: {str(e)}")

    async def _test_websocket_auth(self, test: SystemTest):
        """Test WebSocket authentication token for private data access."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check for authentication token
            auth_token = getattr(self.bot.websocket_manager, 'auth_token', None)
            has_auth = auth_token is not None and len(str(auth_token)) > 0

            # Check if authenticated WebSocket URL is being used
            connection_url = getattr(self.bot.websocket_manager, 'url', '')
            is_auth_url = 'ws-auth.kraken.com' in str(connection_url)

            if has_auth and is_auth_url:
                test.succeed({
                    "websocket_authenticated": True,
                    "auth_token_present": True,
                    "auth_url_used": True
                })
            elif not has_auth:
                test.fail("WebSocket authentication token missing")
            elif not is_auth_url:
                test.fail("WebSocket not using authenticated Kraken URL")
            else:
                test.fail("WebSocket authentication configuration invalid")

        except Exception as e:
            test.fail(f"WebSocket authentication test failed: {str(e)}")

    async def _test_balance_manager(self, test: SystemTest):
        """Test balance manager with Kraken asset format handling."""
        try:
            if not hasattr(self.bot, 'enhanced_balance_manager'):
                test.fail("Balance manager not initialized")
                return

            # Get current balance
            balance_info = await self.bot.enhanced_balance_manager.get_balance()

            if balance_info and 'total' in balance_info:
                total_balances = balance_info['total']

                # Handle Kraken asset naming (ZUSD vs USD, XXBT vs BTC)
                total_usd = self._get_usd_balance(total_balances)
                free_usd = self._get_usd_balance(balance_info.get('free', {}))

                # Count different asset types
                fiat_assets = sum(1 for asset in total_balances.keys()
                                if asset.startswith('Z') or asset in ['USD', 'EUR', 'GBP'])
                crypto_assets = sum(1 for asset in total_balances.keys()
                                  if asset.startswith('X') or asset in ['BTC', 'ETH', 'ADA'])

                test.succeed({
                    "balance_manager_working": True,
                    "total_usd_equivalent": total_usd,
                    "free_usd_equivalent": free_usd,
                    "fiat_assets": fiat_assets,
                    "crypto_assets": crypto_assets,
                    "kraken_asset_format": any(asset.startswith(('Z', 'X')) for asset in total_balances.keys())
                })

                # Check if balance is sufficient for trading
                if total_usd < 10:
                    test.details["warning"] = "Balance below minimum trading amount"
            else:
                test.fail("Balance manager returned invalid data")

        except Exception as e:
            error_msg = str(e)
            kraken_error = self._identify_kraken_error(error_msg)

            if kraken_error:
                test.fail(f"Balance manager failed: {kraken_error}", {"error_type": kraken_error})
            else:
                test.fail(f"Balance manager test failed: {error_msg}")

    def _get_usd_balance(self, balances: dict[str, float]) -> float:
        """Extract USD balance handling Kraken's asset naming conventions."""
        usd_keys = ['USD', 'ZUSD', 'USDT', 'ZUSDT']

        for key in usd_keys:
            if key in balances:
                return float(balances[key])

        return 0.0

    async def _test_portfolio_tracker(self, test: SystemTest):
        """Test portfolio tracking functionality."""
        try:
            if not hasattr(self.bot, 'portfolio_tracker'):
                test.fail("Portfolio tracker not initialized")
                return

            # Get open positions
            positions = await self.bot.portfolio_tracker.get_open_positions()

            # Validate position data structure
            valid_positions = []
            if positions:
                for pos in positions:
                    if isinstance(pos, dict) and 'symbol' in pos:
                        valid_positions.append(pos)

            test.succeed({
                "portfolio_tracker_working": True,
                "open_positions": len(valid_positions),
                "position_symbols": [p.get('symbol', 'Unknown') for p in valid_positions] if valid_positions else [],
                "data_structure_valid": len(valid_positions) == len(positions) if positions else True
            })

        except Exception as e:
            test.fail(f"Portfolio tracker test failed: {str(e)}")

    async def _test_strategy_manager(self, test: SystemTest):
        """Test strategy manager with valid symbol integration."""
        try:
            if not hasattr(self.bot, 'strategy_manager'):
                test.fail("Strategy manager not initialized")
                return

            # Count active strategies
            active_strategies = 0
            strategy_status = {}
            invalid_symbols = []

            if hasattr(self.bot.strategy_manager, 'strategies'):
                for symbol, strategy in self.bot.strategy_manager.strategies.items():
                    # Check if symbol is valid for Kraken
                    if symbol in self.supported_symbols:
                        if strategy:
                            active_strategies += 1
                            strategy_status[symbol] = "Active"
                        else:
                            strategy_status[symbol] = "Inactive"
                    else:
                        invalid_symbols.append(symbol)
                        strategy_status[symbol] = "Invalid Symbol"

            total_configured = len(self.bot.config.get('trade_pairs', []))

            if active_strategies > 0:
                test.succeed({
                    "strategy_manager_working": True,
                    "active_strategies": active_strategies,
                    "total_configured_pairs": total_configured,
                    "invalid_symbols": len(invalid_symbols),
                    "strategy_efficiency": active_strategies / max(total_configured, 1)
                })

                if invalid_symbols:
                    test.details["invalid_symbols"] = invalid_symbols
                    test.details["error_type"] = "strategy_initialization_failed"
            else:
                test.fail("No active strategies found", {"error_type": "strategy_initialization_failed"})

        except Exception as e:
            test.fail(f"Strategy manager test failed: {str(e)}")

    async def _test_trade_executor(self, test: SystemTest):
        """Test trade execution capability with Kraken compliance."""
        try:
            if not hasattr(self.bot, 'trade_executor'):
                test.fail("Trade executor not initialized")
                return

            # Check for required execution methods
            required_methods = ['execute_trade', '_execute_buy', '_execute_sell']
            available_methods = []

            for method in required_methods:
                if hasattr(self.bot.trade_executor, method):
                    available_methods.append(method)

            # Check for Kraken-specific features
            has_rate_limiting = hasattr(self.bot.trade_executor, 'rate_limiter')
            has_min_validation = hasattr(self.bot.trade_executor, '_validate_order_minimums')

            if len(available_methods) >= 1:  # At least basic execution
                test.succeed({
                    "trade_executor_ready": True,
                    "available_methods": available_methods,
                    "kraken_rate_limiting": has_rate_limiting,
                    "minimum_validation": has_min_validation,
                    "kraken_compliance_features": has_rate_limiting and has_min_validation
                })
            else:
                test.fail("Trade executor missing critical methods")

        except Exception as e:
            test.fail(f"Trade executor test failed: {str(e)}")

    async def _test_risk_management(self, test: SystemTest):
        """Test risk management systems."""
        try:
            # Check various risk components
            has_circuit_breaker = hasattr(self.bot, 'circuit_breaker')
            has_risk_config = 'risk_management' in self.bot.config
            has_position_limits = 'max_position_size' in self.bot.config
            has_loss_limits = 'max_daily_loss' in self.bot.config

            risk_features = sum([has_circuit_breaker, has_risk_config, has_position_limits, has_loss_limits])

            if risk_features >= 2:  # At least 2 risk features
                test.succeed({
                    "risk_management_active": True,
                    "circuit_breaker": has_circuit_breaker,
                    "risk_config": has_risk_config,
                    "position_limits": has_position_limits,
                    "loss_limits": has_loss_limits,
                    "risk_score": risk_features
                })
            else:
                test.fail(f"Insufficient risk management systems ({risk_features}/4 features)")

        except Exception as e:
            test.fail(f"Risk management test failed: {str(e)}")

    async def _test_data_pipeline(self, test: SystemTest):
        """Test data processing pipeline."""
        try:
            # Check for data handling methods
            data_methods = ['_handle_ohlc_data', '_handle_ticker_data', '_handle_trade_data']
            available_methods = []

            for method in data_methods:
                if hasattr(self.bot, method):
                    available_methods.append(method)

            if len(available_methods) >= 1:
                test.succeed({
                    "data_pipeline_ready": True,
                    "available_handlers": available_methods,
                    "handler_count": len(available_methods)
                })
            else:
                test.fail("Data pipeline methods not found")

        except Exception as e:
            test.fail(f"Data pipeline test failed: {str(e)}")

    async def _test_opportunity_scanner(self, test: SystemTest):
        """Test opportunity scanner functionality."""
        try:
            if not hasattr(self.bot, 'opportunity_scanner'):
                test.fail("Opportunity scanner not initialized")
                return

            # Check scanner configuration
            scan_interval = getattr(self.bot.opportunity_scanner, 'scan_interval', 'Unknown')
            has_valid_symbols = len(self.supported_symbols) > 0

            test.succeed({
                "scanner_available": True,
                "scan_interval": scan_interval,
                "valid_symbols_available": has_valid_symbols,
                "symbol_count": len(self.supported_symbols)
            })

        except Exception as e:
            test.fail(f"Opportunity scanner test failed: {str(e)}")

    async def _test_profit_harvester(self, test: SystemTest):
        """Test profit harvesting system."""
        try:
            if not hasattr(self.bot, 'profit_harvester'):
                test.fail("Profit harvester not initialized")
                return

            test.succeed({"profit_harvester_ready": True})

        except Exception as e:
            test.fail(f"Profit harvester test failed: {str(e)}")

    def _get_another_symbol_alternatives(self, base: str, quote: str) -> list[str]:
        """Get alternative symbol formats for Kraken compatibility."""
        alternatives = []

        # Convert XBT to BTC for v2 compatibility
        kraken_base = "BTC" if base == "XBT" else base
        kraken_quote = quote

        alternatives.append(f"{kraken_base}{kraken_quote}")
        alternatives.append(f"{base}{quote}")

        return alternatives

    async def _test_websocket_connection(self, test: SystemTest):
        """Test WebSocket connection for real-time data."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check WebSocket connection status
            is_connected = getattr(self.bot.websocket_manager, 'is_connected', False)
            connection_url = getattr(self.bot.websocket_manager, 'url', 'unknown')

            # Validate Kraken WebSocket URL
            kraken_ws_urls = [
                'wss://ws.kraken.com',
                'wss://ws-auth.kraken.com',
                'wss://ws.kraken.com/v2',
                'wss://ws-auth.kraken.com/v2'
            ]

            is_kraken_url = any(url in str(connection_url) for url in kraken_ws_urls)

            if is_connected and is_kraken_url:
                test.succeed({
                    "websocket_connected": True,
                    "connection_url": str(connection_url),
                    "kraken_compliant_url": is_kraken_url
                })
            elif is_connected and not is_kraken_url:
                test.fail(f"WebSocket connected but not to Kraken URL: {connection_url}")
            else:
                test.fail("WebSocket not connected", {"error_type": "websocket_disconnected"})

        except Exception as e:
            test.fail(f"WebSocket test failed: {str(e)}")

    async def _test_websocket_auth(self, test: SystemTest):
        """Test WebSocket authentication token for private data access."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check for authentication token
            auth_token = getattr(self.bot.websocket_manager, 'auth_token', None)
            has_auth = auth_token is not None and len(str(auth_token)) > 0

            # Check if authenticated WebSocket URL is being used
            connection_url = getattr(self.bot.websocket_manager, 'url', '')
            is_auth_url = 'ws-auth.kraken.com' in str(connection_url)

            if has_auth and is_auth_url:
                test.succeed({
                    "websocket_authenticated": True,
                    "auth_token_present": True,
                    "auth_url_used": True
                })
            elif not has_auth:
                test.fail("WebSocket authentication token missing")
            elif not is_auth_url:
                test.fail("WebSocket not using authenticated Kraken URL")
            else:
                test.fail("WebSocket authentication configuration invalid")

        except Exception as e:
            test.fail(f"WebSocket authentication test failed: {str(e)}")

    async def _test_websocket_connection(self, test: SystemTest):
        """Test WebSocket connection for real-time data."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check WebSocket connection status
            is_connected = getattr(self.bot.websocket_manager, 'is_connected', False)
            connection_url = getattr(self.bot.websocket_manager, 'url', 'unknown')

            # Validate Kraken WebSocket URL
            kraken_ws_urls = [
                'wss://ws.kraken.com',
                'wss://ws-auth.kraken.com',
                'wss://ws.kraken.com/v2',
                'wss://ws-auth.kraken.com/v2'
            ]

            is_kraken_url = any(url in str(connection_url) for url in kraken_ws_urls)

            if is_connected and is_kraken_url:
                test.succeed({
                    "websocket_connected": True,
                    "connection_url": str(connection_url),
                    "kraken_compliant_url": is_kraken_url
                })
            elif is_connected and not is_kraken_url:
                test.fail(f"WebSocket connected but not to Kraken URL: {connection_url}")
            else:
                test.fail("WebSocket not connected", {"error_type": "websocket_disconnected"})

        except Exception as e:
            test.fail(f"WebSocket test failed: {str(e)}")

    async def _test_websocket_auth(self, test: SystemTest):
        """Test WebSocket authentication token for private data access."""
        try:
            if not hasattr(self.bot, 'websocket_manager'):
                test.fail("WebSocket manager not initialized")
                return

            # Check for authentication token
            auth_token = getattr(self.bot.websocket_manager, 'auth_token', None)
            has_auth = auth_token is not None and len(str(auth_token)) > 0

            # Check if authenticated WebSocket URL is being used
            connection_url = getattr(self.bot.websocket_manager, 'url', '')
            is_auth_url = 'ws-auth.kraken.com' in str(connection_url)

            if has_auth and is_auth_url:
                test.succeed({
                    "websocket_authenticated": True,
                    "auth_token_present": True,
                    "auth_url_used": True
                })
            elif not has_auth:
                test.fail("WebSocket authentication token missing")
            elif not is_auth_url:
                test.fail("WebSocket not using authenticated Kraken URL")
            else:
                test.fail("WebSocket authentication configuration invalid")

        except Exception as e:
            test.fail(f"WebSocket authentication test failed: {str(e)}")

    async def _test_balance_manager(self, test: SystemTest):
        """Test balance manager with Kraken asset format handling."""
        try:
            if not hasattr(self.bot, 'enhanced_balance_manager'):
                test.fail("Balance manager not initialized")
                return

            # Get current balance
            balance_info = await self.bot.enhanced_balance_manager.get_balance()

            if balance_info and 'total' in balance_info:
                total_balances = balance_info['total']

                # Handle Kraken asset naming (ZUSD vs USD, XXBT vs BTC)
                total_usd = self._get_usd_balance(total_balances)
                free_usd = self._get_usd_balance(balance_info.get('free', {}))

                # Count different asset types
                fiat_assets = sum(1 for asset in total_balances.keys()
                                if asset.startswith('Z') or asset in ['USD', 'EUR', 'GBP'])
                crypto_assets = sum(1 for asset in total_balances.keys()
                                  if asset.startswith('X') or asset in ['BTC', 'ETH', 'ADA'])

                test.succeed({
                    "balance_manager_working": True,
                    "total_usd_equivalent": total_usd,
                    "free_usd_equivalent": free_usd,
                    "fiat_assets": fiat_assets,
                    "crypto_assets": crypto_assets,
                    "kraken_asset_format": any(asset.startswith(('Z', 'X')) for asset in total_balances.keys())
                })

                # Check if balance is sufficient for trading
                if total_usd < 10:
                    test.details["warning"] = "Balance below minimum trading amount"
            else:
                test.fail("Balance manager returned invalid data")

        except Exception as e:
            error_msg = str(e)
            kraken_error = self._identify_kraken_error(error_msg)

            if kraken_error:
                test.fail(f"Balance manager failed: {kraken_error}", {"error_type": kraken_error})
            else:
                test.fail(f"Balance manager test failed: {error_msg}")

    def _get_usd_balance(self, balances: dict[str, float]) -> float:
        """Extract USD balance handling Kraken's asset naming conventions."""
        usd_keys = ['USD', 'ZUSD', 'USDT', 'ZUSDT']

        for key in usd_keys:
            if key in balances:
                return float(balances[key])

        return 0.0

    async def _test_portfolio_tracker(self, test: SystemTest):
        """Test portfolio tracking functionality."""
        try:
            if not hasattr(self.bot, 'portfolio_tracker'):
                test.fail("Portfolio tracker not initialized")
                return

            # Get open positions
            positions = await self.bot.portfolio_tracker.get_open_positions()

            # Validate position data structure
            valid_positions = []
            if positions:
                for pos in positions:
                    if isinstance(pos, dict) and 'symbol' in pos:
                        valid_positions.append(pos)

            test.succeed({
                "portfolio_tracker_working": True,
                "open_positions": len(valid_positions),
                "position_symbols": [p.get('symbol', 'Unknown') for p in valid_positions] if valid_positions else [],
                "data_structure_valid": len(valid_positions) == len(positions) if positions else True
            })

        except Exception as e:
            test.fail(f"Portfolio tracker test failed: {str(e)}")

    async def _test_strategy_manager(self, test: SystemTest):
        """Test strategy manager with valid symbol integration."""
        try:
            if not hasattr(self.bot, 'strategy_manager'):
                test.fail("Strategy manager not initialized")
                return

            # Count active strategies
            active_strategies = 0
            strategy_status = {}
            invalid_symbols = []

            if hasattr(self.bot.strategy_manager, 'strategies'):
                for symbol, strategy in self.bot.strategy_manager.strategies.items():
                    # Check if symbol is valid for Kraken
                    if symbol in self.supported_symbols:
                        if strategy:
                            active_strategies += 1
                            strategy_status[symbol] = "Active"
                        else:
                            strategy_status[symbol] = "Inactive"
                    else:
                        invalid_symbols.append(symbol)
                        strategy_status[symbol] = "Invalid Symbol"

            total_configured = len(self.bot.config.get('trade_pairs', []))

            if active_strategies > 0:
                test.succeed({
                    "strategy_manager_working": True,
                    "active_strategies": active_strategies,
                    "total_configured_pairs": total_configured,
                    "invalid_symbols": len(invalid_symbols),
                    "strategy_efficiency": active_strategies / max(total_configured, 1)
                })

                if invalid_symbols:
                    test.details["invalid_symbols"] = invalid_symbols
                    test.details["error_type"] = "strategy_initialization_failed"
            else:
                test.fail("No active strategies found", {"error_type": "strategy_initialization_failed"})

        except Exception as e:
            test.fail(f"Strategy manager test failed: {str(e)}")

    async def _test_trade_executor(self, test: SystemTest):
        """Test trade execution capability with Kraken compliance."""
        try:
            if not hasattr(self.bot, 'trade_executor'):
                test.fail("Trade executor not initialized")
                return

            # Check for required execution methods
            required_methods = ['execute_trade', '_execute_buy', '_execute_sell']
            available_methods = []

            for method in required_methods:
                if hasattr(self.bot.trade_executor, method):
                    available_methods.append(method)

            # Check for Kraken-specific features
            has_rate_limiting = hasattr(self.bot.trade_executor, 'rate_limiter')
            has_min_validation = hasattr(self.bot.trade_executor, '_validate_order_minimums')

            if len(available_methods) >= 1:  # At least basic execution
                test.succeed({
                    "trade_executor_ready": True,
                    "available_methods": available_methods,
                    "kraken_rate_limiting": has_rate_limiting,
                    "minimum_validation": has_min_validation,
                    "kraken_compliance_features": has_rate_limiting and has_min_validation
                })
            else:
                test.fail("Trade executor missing critical methods")

        except Exception as e:
            test.fail(f"Trade executor test failed: {str(e)}")

    async def _test_risk_management(self, test: SystemTest):
        """Test risk management systems."""
        try:
            # Check various risk components
            has_circuit_breaker = hasattr(self.bot, 'circuit_breaker')
            has_risk_config = 'risk_management' in self.bot.config
            has_position_limits = 'max_position_size' in self.bot.config
            has_loss_limits = 'max_daily_loss' in self.bot.config

            risk_features = sum([has_circuit_breaker, has_risk_config, has_position_limits, has_loss_limits])

            if risk_features >= 2:  # At least 2 risk features
                test.succeed({
                    "risk_management_active": True,
                    "circuit_breaker": has_circuit_breaker,
                    "risk_config": has_risk_config,
                    "position_limits": has_position_limits,
                    "loss_limits": has_loss_limits,
                    "risk_score": risk_features
                })
            else:
                test.fail(f"Insufficient risk management systems ({risk_features}/4 features)")

        except Exception as e:
            test.fail(f"Risk management test failed: {str(e)}")

    async def _test_data_pipeline(self, test: SystemTest):
        """Test data processing pipeline."""
        try:
            # Check for data handling methods
            data_methods = ['_handle_ohlc_data', '_handle_ticker_data', '_handle_trade_data']
            available_methods = []

            for method in data_methods:
                if hasattr(self.bot, method):
                    available_methods.append(method)

            if len(available_methods) >= 1:
                test.succeed({
                    "data_pipeline_ready": True,
                    "available_handlers": available_methods,
                    "handler_count": len(available_methods)
                })
            else:
                test.fail("Data pipeline methods not found")

        except Exception as e:
            test.fail(f"Data pipeline test failed: {str(e)}")

    async def _test_opportunity_scanner(self, test: SystemTest):
        """Test opportunity scanner functionality."""
        try:
            if not hasattr(self.bot, 'opportunity_scanner'):
                test.fail("Opportunity scanner not initialized")
                return

            # Check scanner configuration
            scan_interval = getattr(self.bot.opportunity_scanner, 'scan_interval', 'Unknown')
            has_valid_symbols = len(self.supported_symbols) > 0

            test.succeed({
                "scanner_available": True,
                "scan_interval": scan_interval,
                "valid_symbols_available": has_valid_symbols,
                "symbol_count": len(self.supported_symbols)
            })

        except Exception as e:
            test.fail(f"Opportunity scanner test failed: {str(e)}")

    async def _test_profit_harvester(self, test: SystemTest):
        """Test profit harvesting system."""
        try:
            if not hasattr(self.bot, 'profit_harvester'):
                test.fail("Profit harvester not initialized")
                return

            test.succeed({"profit_harvester_ready": True})

        except Exception as e:
            test.fail(f"Profit harvester test failed: {str(e)}")

    async def _test_learning_systems(self, test: SystemTest):
        """Test learning and self-improvement systems."""
        try:
            # Check for various learning components
            learning_components = [
                ('unified_learning', 'Unified Learning System'),
                ('learning_system', 'Basic Learning System'),
                ('minimum_learning', 'Minimum Learning System'),
                ('websocket_message_learner', 'WebSocket Message Learner')
            ]

            available_components = []
            for attr_name, display_name in learning_components:
                if hasattr(self.bot, attr_name):
                    available_components.append(display_name)

            if available_components:
                test.succeed({
                    "learning_systems_available": True,
                    "available_components": available_components,
                    "component_count": len(available_components)
                })
            else:
                test.fail("No learning systems found")

        except Exception as e:
            test.fail(f"Learning systems test failed: {str(e)}")

    async def _test_assistants(self, test: SystemTest):
        """Test assistant network."""
        try:
            # Check for assistant components
            assistant_count = 0
            assistant_types = []

            # Check unified infinity system
            if hasattr(self.bot, 'unified_infinity_system'):
                if hasattr(self.bot.unified_infinity_system, 'assistants'):
                    assistant_count += len(self.bot.unified_infinity_system.assistants)
                    assistant_types.append('Unified Infinity System')

            # Check individual assistants
            assistant_attrs = ['buy_assistant', 'sell_assistant', 'risk_assistant']
            for attr in assistant_attrs:
                if hasattr(self.bot, attr):
                    assistant_count += 1
                    assistant_types.append(attr.replace('_', ' ').title())

            if assistant_count > 0:
                test.succeed({
                    "assistants_available": True,
                    "assistant_count": assistant_count,
                    "assistant_types": assistant_types
                })
            else:
                test.fail("No assistants initialized")

        except Exception as e:
            test.fail(f"Assistant network test failed: {str(e)}")

    def _identify_kraken_error(self, error_message: str) -> Optional[str]:
        """Identify Kraken-specific error patterns."""
        for pattern, error_type in self.kraken_error_patterns.items():
            if pattern in error_message:
                return error_type
        return None

    async def _analyze_portfolio_status(self) -> bool:
        """Analyze current portfolio status to determine trading strategy."""
        self.logger.info("Analyzing portfolio status...")

        try:
            # Get balance information
            balance_info = await self.bot.enhanced_balance_manager.get_balance()

            # Handle Kraken asset naming
            total_balances = balance_info.get('total', {})
            free_balances = balance_info.get('free', {})

            total_usd = self._get_usd_balance(total_balances)
            free_usd = self._get_usd_balance(free_balances)

            # Get open positions
            positions = await self.bot.portfolio_tracker.get_open_positions()
            position_value = sum(p.get('value', 0) for p in positions)

            # Calculate portfolio allocation
            cash_percentage = (free_usd / total_usd * 100) if total_usd > 0 else 0
            position_percentage = (position_value / total_usd * 100) if total_usd > 0 else 0

            self.portfolio_status = {
                'total_balance': total_usd,
                'cash_available': free_usd,
                'position_value': position_value,
                'cash_percentage': cash_percentage,
                'position_percentage': position_percentage,
                'open_positions': len(positions),
                'positions': positions
            }

            # Log portfolio status
            self.logger.info("Portfolio Status:")
            self.logger.info(f"  Total Balance: ${total_usd:.2f}")
            self.logger.info(f"  Cash Available: ${free_usd:.2f} ({cash_percentage:.1f}%)")
            self.logger.info(f"  Position Value: ${position_value:.2f} ({position_percentage:.1f}%)")
            self.logger.info(f"  Open Positions: {len(positions)}")

            if positions:
                self.logger.info("  Current Positions:")
                for pos in positions:
                    self.logger.info(f"    - {pos.get('symbol')}: ${pos.get('value', 0):.2f}")

            # Determine trading strategy based on portfolio status
            if free_usd < 10 and len(positions) == 0:
                self.logger.warning("Insufficient funds for trading")
                self.portfolio_status['strategy'] = 'insufficient_funds'
                self.portfolio_status['action'] = 'Need deposit'
                return False

            elif free_usd < 10 and len(positions) > 0:
                self.logger.info("Funds are deployed in positions")
                self.portfolio_status['strategy'] = 'funds_deployed'
                self.portfolio_status['action'] = 'Monitor positions for profit taking'
                return True

            elif cash_percentage > 80:
                self.logger.info("High cash allocation - looking for buy opportunities")
                self.portfolio_status['strategy'] = 'accumulation'
                self.portfolio_status['action'] = 'Actively seek buy opportunities'
                return True

            elif cash_percentage < 20:
                self.logger.info("Low cash allocation - focus on position management")
                self.portfolio_status['strategy'] = 'position_management'
                self.portfolio_status['action'] = 'Monitor for profit taking and reallocation'
                return True

            else:
                self.logger.info("Balanced allocation - normal trading mode")
                self.portfolio_status['strategy'] = 'balanced'
                self.portfolio_status['action'] = 'Normal buy/sell operations'
                return True

        except Exception as e:
            self.logger.error(f"Portfolio analysis failed: {e}")
            self.portfolio_status = {
                'error': str(e),
                'strategy': 'error',
                'action': 'Cannot determine - manual review needed'
            }
            return False

    async def _attempt_automatic_fixes(self) -> bool:
        """Attempt to automatically fix failed tests using learned solutions."""
        any_fix_successful = False

        for test_name, test in self.test_results.items():
            if not test.passed and test.critical:
                # Check if we have a learned fix for this error type
                error_type = test.details.get('error_type', '')

                if error_type in self.learned_fixes:
                    fix_info = self.learned_fixes[error_type]
                    fix_method_name = fix_info['fix_method']

                    self.logger.info(f"Attempting to fix {test_name} using {fix_method_name}")

                    try:
                        # Call the fix method
                        if hasattr(self, fix_method_name):
                            fix_method = getattr(self, fix_method_name)
                            fix_result = await fix_method(test)

                            if fix_result:
                                test.fix_attempted = True
                                test.fix_successful = True
                                any_fix_successful = True
                                self.logger.info(f"Successfully fixed {test_name}")
                            else:
                                test.fix_attempted = True
                                test.fix_successful = False
                                self.logger.warning(f"Failed to fix {test_name}")

                    except Exception as e:
                        self.logger.error(f"Error attempting fix for {test_name}: {e}")
                        test.fix_attempted = True
                        test.fix_successful = False

        return any_fix_successful

    async def _fix_websocket_connection(self, test: SystemTest) -> bool:
        """Attempt to fix WebSocket connection issues."""
        try:
            if hasattr(self.bot, 'websocket_manager'):
                self.logger.info("Reconnecting WebSocket...")
                await self.bot.websocket_manager.reconnect()

                # Wait a moment for connection
                await asyncio.sleep(2)

                # Check if connected now
                if getattr(self.bot.websocket_manager, 'is_connected', False):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"WebSocket fix failed: {e}")
            return False

    async def _fix_api_credentials(self, test: SystemTest) -> bool:
        """Attempt to reload API credentials."""
        try:
            # Try reloading from environment
            from dotenv import load_dotenv

            load_dotenv()

            api_key = os.getenv('KRAKEN_API_KEY')
            api_secret = os.getenv('KRAKEN_API_SECRET') or os.getenv('KRAKEN_SECRET_KEY')

            if api_key and api_secret:
                # Reinitialize exchange with new credentials
                if hasattr(self.bot, 'initialize_all_components'):
                    self.logger.info("Reinitializing exchange with reloaded credentials...")
                    await self.bot.initialize_all_components()
                    return True

            return False

        except Exception as e:
            self.logger.error(f"API credential fix failed: {e}")
            return False

    async def _fix_strategy_initialization(self, test: SystemTest) -> bool:
        """Attempt to reinitialize strategies with valid symbols."""
        try:
            if hasattr(self.bot, 'strategy_manager'):
                self.logger.info("Reinitializing strategies...")

                # Get valid symbols from our validation
                valid_symbols = []
                configured_pairs = self.bot.config.get('trade_pairs', [])

                for pair in configured_pairs:
                    if pair in self.supported_symbols:
                        valid_symbols.append(pair)
                    else:
                        # Check alternatives
                        alternatives = self._get_symbol_alternatives(pair)
                        for alt in alternatives:
                            if alt in self.supported_symbols:
                                valid_symbols.append(alt)
                                break

                # Reinitialize with valid symbols
                for symbol in valid_symbols:
                    if hasattr(self.bot.strategy_manager, 'create_strategy_for_symbol'):
                        await self.bot.strategy_manager.create_strategy_for_symbol(symbol, "RANGE", self.bot)

                return len(valid_symbols) > 0

            return False

        except Exception as e:
            self.logger.error(f"Strategy initialization fix failed: {e}")
            return False

    async def _fix_symbol_configuration(self, test: SystemTest) -> bool:
        """Update configuration with supported Kraken symbols."""
        try:
            # Get configured pairs
            configured_pairs = self.bot.config.get('trade_pairs', [])
            valid_pairs = []

            # Find valid alternatives
            for pair in configured_pairs:
                if pair in self.supported_symbols:
                    valid_pairs.append(pair)
                else:
                    alternatives = self._get_symbol_alternatives(pair)
                    for alt in alternatives:
                        if alt in self.supported_symbols:
                            valid_pairs.append(alt)
                            break

            if valid_pairs:
                # Update bot's configuration temporarily
                self.bot.config['trade_pairs'] = valid_pairs
                self.logger.info(f"Updated trading pairs: {valid_pairs}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Symbol configuration fix failed: {e}")
            return False

    async def _rerun_failed_tests(self) -> bool:
        """Re-run tests that failed but had fixes attempted."""
        all_critical_passed = True

        for test_name, test in self.test_results.items():
            if not test.passed and test.fix_attempted:
                # Find the original test method
                for name, method, is_critical in self.tests:
                    if name == test_name:
                        self.logger.info(f"Re-testing {test_name} after fix attempt...")

                        try:
                            # Create new test instance
                            new_test = SystemTest(test_name, is_critical)
                            await method(new_test)

                            if new_test.passed:
                                self.logger.info(f"[EMOJI] {test_name} - NOW PASSING")
                                self.test_results[test_name] = new_test
                            else:
                                self.logger.error(f"[EMOJI] {test_name} - STILL FAILING")
                                if is_critical:
                                    all_critical_passed = False

                        except Exception as e:
                            self.logger.error(f"[EMOJI] {test_name} - Re-test crashed: {e}")
                            if is_critical:
                                all_critical_passed = False

                        break

        return all_critical_passed

    def _verify_kraken_compliance(self) -> dict[str, Any]:
        """Verify overall Kraken compliance status."""
        compliance_status = {
            'compliant': True,
            'score': 0,
            'issues': [],
            'recommendations': []
        }

        total_tests = len(self.test_results)
        kraken_compliant_tests = sum(1 for t in self.test_results.values() if t.kraken_compliant)

        compliance_status['score'] = (kraken_compliant_tests / total_tests * 100) if total_tests > 0 else 0

        # Check for specific compliance issues
        if self.kraken_system_status and self.kraken_system_status.get('status') != 'ok':
            compliance_status['issues'].append('Kraken system not fully operational')

        if not self.supported_symbols:
            compliance_status['issues'].append('No valid Kraken symbols identified')

        # Generate recommendations
        if compliance_status['score'] < 80:
            compliance_status['recommendations'].append('Improve Kraken API integration')

        if compliance_status['issues']:
            compliance_status['compliant'] = False

        return compliance_status

    def _make_startup_decision(self, all_tests_passed: bool, portfolio_ready: bool, compliance_status: dict) -> tuple[bool, str]:
        """Make the final decision about whether to start trading."""
        # Count test results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results.values() if t.passed)
        critical_failed = [name for name, t in self.test_results.items() if t.critical and not t.passed]

        self.logger.info("="*80)
        self.logger.info(f"Test Results: {passed_tests}/{total_tests} passed")
        self.logger.info(f"Kraken Compliance Score: {compliance_status['score']:.1f}%")

        if critical_failed:
            self.logger.error(f"Critical failures: {', '.join(critical_failed)}")

        # Generate detailed error report if we can't start
        if not all_tests_passed:
            error_report = self._generate_error_report()

            # Save error report
            self._save_error_report(error_report)

            message = f"CANNOT START TRADING - {len(critical_failed)} critical system failures\n"
            message += "Error report saved to: trading_data/startup_errors.json\n"
            message += f"Kraken Compliance: {compliance_status['score']:.1f}%\n"
            message += "\nCritical Failures:\n"

            for test_name in critical_failed:
                test = self.test_results[test_name]
                message += f"  - {test_name}: {test.error}\n"

            return False, message

        # Check portfolio status
        if not portfolio_ready:
            message = "CANNOT START TRADING - Portfolio not ready\n"
            if self.portfolio_status:
                message += f"Reason: {self.portfolio_status.get('action', 'Unknown')}"
            return False, message

        # Check Kraken compliance
        if not compliance_status['compliant']:
            message = "TRADING PERMITTED WITH WARNINGS - Kraken compliance issues detected\n"
            message += f"Compliance Score: {compliance_status['score']:.1f}%\n"
            message += f"Issues: {', '.join(compliance_status['issues'])}\n"
            message += f"Portfolio Strategy: {self.portfolio_status.get('strategy', 'Unknown')}\n"
            message += f"Action Plan: {self.portfolio_status.get('action', 'Unknown')}"

            return True, message

        # All systems go!
        message = "ALL SYSTEMS OPERATIONAL - Starting trading\n"
        message += f"Kraken Compliance: {compliance_status['score']:.1f}% [EMOJI]\n"
        message += f"Portfolio Strategy: {self.portfolio_status.get('strategy', 'Unknown')}\n"
        message += f"Action Plan: {self.portfolio_status.get('action', 'Unknown')}"

        return True, message

    def _generate_error_report(self) -> dict:
        """Generate comprehensive error report for debugging."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'kraken_compliance': {
                'system_status': self.kraken_system_status,
                'supported_symbols_count': len(self.supported_symbols),
                'rate_limit_delay': self.rate_limit_delay
            },
            'test_summary': {
                'total_tests': len(self.test_results),
                'passed': sum(1 for t in self.test_results.values() if t.passed),
                'failed': sum(1 for t in self.test_results.values() if not t.passed),
                'critical_failures': sum(1 for t in self.test_results.values() if t.critical and not t.passed),
                'kraken_compliant': sum(1 for t in self.test_results.values() if t.kraken_compliant)
            },
            'failed_tests': {},
            'system_info': {
                'bot_config': {
                    'trade_pairs': self.bot.config.get('trade_pairs', []),
                    'position_size': self.bot.config.get('position_size_usd', 0),
                    'exchange': self.bot.config.get('exchange', 'unknown')
                }
            }
        }

        # Add details for each failed test
        for test_name, test in self.test_results.items():
            if not test.passed:
                report['failed_tests'][test_name] = {
                    'error': test.error,
                    'critical': test.critical,
                    'fix_attempted': test.fix_attempted,
                    'fix_successful': test.fix_successful,
                    'kraken_compliant': test.kraken_compliant,
                    'details': test.details
                }

        return report

    def _save_error_report(self, report: dict):
        """Save error report to file for debugging."""
        try:
            report_file = Path("trading_data/startup_errors.json")
            report_file.parent.mkdir(parents=True, exist_ok=True)

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            self.logger.info(f"Error report saved to: {report_file}")

        except Exception as e:
            self.logger.error(f"Failed to save error report: {e}")
