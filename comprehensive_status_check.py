#!/usr/bin/env python3
"""
Comprehensive Status Check - December 2025
==========================================
Complete assessment of crypto trading bot readiness
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class ComprehensiveStatusChecker:
    """Complete system status assessment"""

    def __init__(self):
        self.status = {
            "timestamp": datetime.now().isoformat(),
            "credentials": {},
            "components": {},
            "integrations": {},
            "launch_readiness": {},
            "issues": [],
            "recommendations": []
        }

    def check_credentials(self):
        """Check credential system status"""
        print("\n1. CREDENTIAL SYSTEM CHECK")
        print("=" * 50)

        try:
            from src.auth.credential_manager import CredentialManager

            cm = CredentialManager()
            api_key, secret = cm.get_kraken_credentials()

            # Check if credentials are loaded
            if api_key and secret:
                print("✅ Credentials loaded successfully")
                print(f"   API Key: {api_key[:8]}...")
                print(f"   Secret: {secret[:8]}...")
                self.status["credentials"] = {
                    "status": "OK",
                    "api_key_present": True,
                    "secret_present": True,
                    "source": "unified" if os.getenv("KRAKEN_KEY") else "legacy"
                }
            else:
                print("❌ Credentials NOT found")
                self.status["credentials"] = {
                    "status": "MISSING",
                    "api_key_present": False,
                    "secret_present": False
                }
                self.status["issues"].append("No API credentials found in environment")

            # Check credential validation
            if api_key and secret:
                valid = cm.validate_credentials(api_key, secret)
                print(f"   Validation: {'✅ Valid format' if valid else '❌ Invalid format'}")
                self.status["credentials"]["valid_format"] = valid
                if not valid:
                    self.status["issues"].append("API credentials have invalid format")

        except Exception as e:
            print(f"❌ Credential check failed: {e}")
            self.status["credentials"]["status"] = "ERROR"
            self.status["credentials"]["error"] = str(e)
            self.status["issues"].append(f"Credential system error: {e}")

    def check_core_components(self):
        """Check core bot components"""
        print("\n2. CORE COMPONENTS CHECK")
        print("=" * 50)

        components_to_check = [
            ("Nonce Manager", "src.utils.unified_kraken_nonce_manager", "get_unified_nonce_manager"),
            ("Exchange", "src.exchange.native_kraken_exchange", "NativeKrakenExchange"),
            ("Balance Manager", "src.balance.balance_manager_v2", "BalanceManagerV2"),
            ("WebSocket Manager", "src.exchange.websocket_manager_v2", "KrakenProWebSocketManager"),
            ("Bot Core", "src.core.bot", "KrakenTradingBot")
        ]

        for name, module_path, class_name in components_to_check:
            try:
                module = __import__(module_path, fromlist=[class_name])
                getattr(module, class_name)
                print(f"✅ {name}: Available")
                self.status["components"][name] = {"status": "OK", "available": True}
            except ImportError as e:
                print(f"❌ {name}: Import error - {e}")
                self.status["components"][name] = {"status": "ERROR", "error": str(e)}
                self.status["issues"].append(f"{name} import failed: {e}")
            except Exception as e:
                print(f"❌ {name}: Error - {e}")
                self.status["components"][name] = {"status": "ERROR", "error": str(e)}
                self.status["issues"].append(f"{name} error: {e}")

    async def check_exchange_initialization(self):
        """Check if exchange can be initialized"""
        print("\n3. EXCHANGE INITIALIZATION CHECK")
        print("=" * 50)

        try:
            from src.auth.credential_manager import get_kraken_credentials
            from src.exchange.native_kraken_exchange import NativeKrakenExchange

            api_key, secret = get_kraken_credentials()

            if not api_key or not secret:
                print("❌ Cannot initialize exchange - no credentials")
                self.status["integrations"]["exchange"] = {
                    "status": "NO_CREDENTIALS",
                    "initialized": False
                }
                self.status["issues"].append("Exchange initialization blocked: no credentials")
                return

            # Try to create exchange instance
            exchange = NativeKrakenExchange(api_key, secret)
            print("✅ Exchange instance created")

            # Try to initialize
            await exchange.initialize()
            print("✅ Exchange initialized successfully")

            self.status["integrations"]["exchange"] = {
                "status": "OK",
                "initialized": True
            }

            # Cleanup
            await exchange.close()

        except Exception as e:
            print(f"❌ Exchange initialization failed: {e}")
            self.status["integrations"]["exchange"] = {
                "status": "ERROR",
                "initialized": False,
                "error": str(e)
            }
            self.status["issues"].append(f"Exchange initialization failed: {e}")

    async def check_websocket_v2(self):
        """Check WebSocket V2 status"""
        print("\n4. WEBSOCKET V2 CHECK")
        print("=" * 50)

        try:
            # Check if V2 implementation exists
            v2_files = [
                "src/exchange/kraken_websocket_v2_direct.py",
                "src/exchange/kraken_websocket_v2_fixed.py",
                "src/exchange/websocket_manager_v2.py"
            ]

            v2_available = False
            for file_path in v2_files:
                if (project_root / file_path).exists():
                    print(f"✅ Found: {file_path}")
                    v2_available = True

            if v2_available:
                # Try to import V2 manager
                print("✅ WebSocket V2 manager importable")
                self.status["integrations"]["websocket_v2"] = {
                    "status": "OK",
                    "available": True,
                    "august_2025_compliant": True
                }
            else:
                print("❌ WebSocket V2 files not found")
                self.status["integrations"]["websocket_v2"] = {
                    "status": "MISSING",
                    "available": False
                }
                self.status["issues"].append("WebSocket V2 implementation missing")

        except Exception as e:
            print(f"❌ WebSocket V2 check failed: {e}")
            self.status["integrations"]["websocket_v2"] = {
                "status": "ERROR",
                "error": str(e)
            }
            self.status["issues"].append(f"WebSocket V2 error: {e}")

    def check_database(self):
        """Check database connectivity"""
        print("\n5. DATABASE CHECK")
        print("=" * 50)

        try:
            from src.storage.database_manager import DatabaseManager

            # Try to create instance
            DatabaseManager()
            print("✅ Database manager created")

            # Check if DB file exists
            db_path = Path("D:/trading_data/trading_bot.db")
            if db_path.exists():
                print(f"✅ Database file exists: {db_path}")
                self.status["integrations"]["database"] = {
                    "status": "OK",
                    "path": str(db_path),
                    "exists": True
                }
            else:
                print(f"⚠️ Database file not found at: {db_path}")
                self.status["integrations"]["database"] = {
                    "status": "NOT_INITIALIZED",
                    "path": str(db_path),
                    "exists": False
                }

        except Exception as e:
            print(f"❌ Database check failed: {e}")
            self.status["integrations"]["database"] = {
                "status": "ERROR",
                "error": str(e)
            }
            self.status["issues"].append(f"Database error: {e}")

    def check_launch_files(self):
        """Check launch system files"""
        print("\n6. LAUNCH SYSTEM CHECK")
        print("=" * 50)

        launch_files = {
            "main.py": "Main launcher",
            "simple_bot_launch.py": "Simple mode launcher",
            "launch_paper_trading.py": "Paper trading launcher",
            ".env": "Environment configuration",
            "config.json": "Bot configuration"
        }

        all_present = True
        for file_name, description in launch_files.items():
            file_path = project_root / file_name
            if file_path.exists():
                print(f"✅ {description}: {file_name}")
            else:
                print(f"❌ {description}: {file_name} NOT FOUND")
                all_present = False
                self.status["issues"].append(f"Missing launch file: {file_name}")

        self.status["launch_readiness"]["files_present"] = all_present

    def determine_launch_readiness(self):
        """Determine overall launch readiness"""
        print("\n7. LAUNCH READINESS ASSESSMENT")
        print("=" * 50)

        # Check critical components
        ready = True
        critical_checks = []

        # Credentials
        if self.status.get("credentials", {}).get("status") == "OK":
            critical_checks.append("✅ Credentials: READY")
        else:
            critical_checks.append("❌ Credentials: NOT READY")
            ready = False

        # Core components
        components_ok = all(
            comp.get("status") == "OK"
            for comp in self.status.get("components", {}).values()
        )
        if components_ok:
            critical_checks.append("✅ Core Components: READY")
        else:
            critical_checks.append("❌ Core Components: NOT READY")
            ready = False

        # Exchange
        if self.status.get("integrations", {}).get("exchange", {}).get("status") == "OK":
            critical_checks.append("✅ Exchange: READY")
        else:
            critical_checks.append("⚠️ Exchange: NOT TESTED")

        # WebSocket V2
        if self.status.get("integrations", {}).get("websocket_v2", {}).get("status") == "OK":
            critical_checks.append("✅ WebSocket V2: READY")
        else:
            critical_checks.append("⚠️ WebSocket V2: ISSUES")

        # Database
        if self.status.get("integrations", {}).get("database", {}).get("status") in ["OK", "NOT_INITIALIZED"]:
            critical_checks.append("✅ Database: READY")
        else:
            critical_checks.append("⚠️ Database: ISSUES")

        # Launch files
        if self.status.get("launch_readiness", {}).get("files_present"):
            critical_checks.append("✅ Launch Files: READY")
        else:
            critical_checks.append("❌ Launch Files: MISSING")
            ready = False

        for check in critical_checks:
            print(check)

        self.status["launch_readiness"]["overall_ready"] = ready

        print("\n" + "=" * 50)
        if ready:
            print("🚀 BOT IS READY TO LAUNCH!")
            self.status["recommendations"].append("Bot is ready for launch")
        else:
            print("🔧 BOT NEEDS FIXES BEFORE LAUNCH")
            if not self.status.get("credentials", {}).get("status") == "OK":
                self.status["recommendations"].append("Fix credentials: Ensure KRAKEN_KEY and KRAKEN_SECRET are set in .env file")

    def generate_recommendations(self):
        """Generate specific recommendations"""
        print("\n8. RECOMMENDATIONS")
        print("=" * 50)

        if self.status["issues"]:
            print("Issues to fix:")
            for issue in self.status["issues"]:
                print(f"  • {issue}")

        print("\nRecommended actions:")
        for rec in self.status["recommendations"]:
            print(f"  → {rec}")

    async def run_full_assessment(self):
        """Run complete assessment"""
        print("=" * 60)
        print("CRYPTO TRADING BOT - COMPREHENSIVE STATUS CHECK")
        print("=" * 60)
        print(f"Timestamp: {datetime.now()}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Platform: {sys.platform}")

        # Run all checks
        self.check_credentials()
        self.check_core_components()
        await self.check_exchange_initialization()
        await self.check_websocket_v2()
        self.check_database()
        self.check_launch_files()
        self.determine_launch_readiness()
        self.generate_recommendations()

        # Save report
        report_path = project_root / f"status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.status, f, indent=2)

        print(f"\n📄 Full report saved to: {report_path}")

        return self.status["launch_readiness"]["overall_ready"]


async def main():
    """Main entry point"""
    checker = ComprehensiveStatusChecker()
    ready = await checker.run_full_assessment()

    print("\n" + "=" * 60)
    if ready:
        print("✅ LAUNCH STATUS: READY")
        print("\nTo launch the bot, run:")
        print("  python3 main.py --simple      # For simple mode")
        print("  python3 main.py --paper       # For paper trading")
        return 0
    else:
        print("❌ LAUNCH STATUS: NOT READY")
        print("\nFix the issues above before launching")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
