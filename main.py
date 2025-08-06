#!/usr/bin/env python3
"""
UNIFIED CRYPTO TRADING BOT LAUNCHER
====================================

This is the main entry point for the crypto trading bot.
Provides multiple launch modes with unified interface.

Usage:
    python main.py                    # Interactive mode selection
    python main.py --simple           # Simple bot launch
    python main.py --orchestrated     # Full orchestrated mode
    python main.py --paper            # Paper trading mode
    python main.py --test             # Test components only
    python main.py --status           # Check bot status
    python main.py --help             # Show all options

Environment Support:
    - Windows (native)
    - WSL/Linux
    - Handles both development and production setups
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Setup credential loading based on environment
import platform

if platform.system() == 'Windows':
    # Native Windows - try to sync system environment variables
    try:
        # Check if we have system environment variables
        import os
        has_system_creds = (os.environ.get('KRAKEN_KEY') or os.environ.get('KRAKEN_API_KEY'))

        if has_system_creds and not os.getenv('KRAKEN_KEY'):
            # System vars exist but not in loaded environment - fix it
            from fix_windows_credentials import fix_credential_loading
            if fix_credential_loading():
                print("✓ Windows credentials synchronized from system environment")
    except Exception as e:
        print(f"Note: Could not sync Windows credentials: {e}")
else:
    # WSL/Linux - try Windows environment bridge
    try:
        from src.utils.windows_env_bridge import WSL_ENVIRONMENT, setup_kraken_credentials
        if WSL_ENVIRONMENT:
            print("Detected WSL environment - setting up Windows environment bridge...")
            bridge_success = setup_kraken_credentials()
            if bridge_success:
                print("✓ Windows environment bridge setup successful")
            else:
                print("⚠ Windows environment bridge setup failed - will try other credential sources")
    except ImportError:
        pass
    except Exception as e:
        print(f"Warning: Windows environment bridge setup error: {e}")

# Fix Windows event loop
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# Core imports
from src.utils.custom_logging import configure_logging


class UnifiedLauncher:
    """Unified launcher for all bot modes"""

    def __init__(self):
        self.project_root = project_root
        self.logger = None
        self.setup_logging()

    def setup_logging(self):
        """Setup basic logging"""
        try:
            self.logger = configure_logging()
            self.logger.info("=" * 60)
            self.logger.info("CRYPTO TRADING BOT - UNIFIED LAUNCHER")
            self.logger.info("=" * 60)
            self.logger.info(f"Launch time: {datetime.now()}")
            self.logger.info(f"Project root: {self.project_root}")
            self.logger.info(f"Python version: {sys.version}")
            self.logger.info(f"Platform: {sys.platform}")
        except Exception as e:
            print(f"WARNING: Failed to setup logging: {e}")
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)

    def check_environment(self) -> dict[str, Any]:
        """Check environment and dependencies"""
        env_status = {
            "python_version": sys.version,
            "platform": sys.platform,
            "project_root_exists": self.project_root.exists(),
            "config_exists": (self.project_root / "config.json").exists(),
            "env_file_exists": (self.project_root / ".env").exists(),
            "src_directory_exists": (self.project_root / "src").exists(),
            "requirements_exist": (self.project_root / "requirements.txt").exists(),
            "paper_trading_available": False,
            "orchestrated_mode_available": False,
            "simple_mode_available": False,
            "credentials_configured": False,
            "credentials_error": None
        }

        # Check credential configuration
        try:
            from src.auth.credential_manager import get_credential_status
            credential_status = get_credential_status()

            # Check if we have valid credentials
            has_valid_unified = credential_status['unified_credentials']['found'] and credential_status['unified_credentials']['valid']
            has_valid_generic = credential_status['generic_credentials']['found'] and credential_status['generic_credentials']['valid']

            if has_valid_unified or has_valid_generic:
                # Double-check that credentials are not placeholder values
                from src.auth.credential_manager import get_kraken_credentials
                api_key, private_key = get_kraken_credentials()

                if api_key and private_key:
                    # Check for placeholder values
                    placeholder_values = ['YOUR_NEW_API_KEY_HERE', 'YOUR_NEW_API_SECRET_HERE', 'YOUR_API_KEY_HERE', 'YOUR_API_SECRET_HERE']
                    if api_key not in placeholder_values and private_key not in placeholder_values:
                        env_status["credentials_configured"] = True
                    else:
                        env_status["credentials_error"] = "Placeholder values found in .env file - please configure with real API keys"
                else:
                    env_status["credentials_error"] = "No credentials returned from credential manager"
            else:
                env_status["credentials_error"] = "No valid credentials found in environment variables or .env file"

        except Exception as e:
            env_status["credentials_error"] = f"Error checking credentials: {e}"

        # Check for paper trading
        try:
            from src.paper_trading.integration import get_paper_integration
            env_status["paper_trading_available"] = True
        except ImportError:
            pass

        # Check for orchestrated mode
        if (self.project_root / "main_orchestrated.py").exists():
            env_status["orchestrated_mode_available"] = True

        # Check for simple mode (check if KrakenTradingBot is importable)
        try:
            from src.core.bot import KrakenTradingBot
            env_status["simple_mode_available"] = True
        except ImportError:
            pass

        return env_status

    def display_environment_status(self, env_status: dict[str, Any]):
        """Display current environment status"""
        print("\n" + "=" * 50)
        print("ENVIRONMENT STATUS")
        print("=" * 50)

        print(f"Python Version: {env_status['python_version'].split()[0]}")
        print(f"Platform: {env_status['platform']}")
        print(f"Project Root: {self.project_root}")

        # Core files
        print("\nCore Files:")
        print(f"  Config file: {'✓' if env_status['config_exists'] else '✗'}")
        print(f"  Environment file: {'✓' if env_status['env_file_exists'] else '✗'}")
        print(f"  Source directory: {'✓' if env_status['src_directory_exists'] else '✗'}")
        print(f"  Requirements: {'✓' if env_status['requirements_exist'] else '✗'}")

        # Credential status
        print("\nCredential Configuration:")
        if env_status['credentials_configured']:
            print("  API Credentials: ✓ Configured and valid")
        else:
            print("  API Credentials: ✗ Not configured or invalid")
            if env_status['credentials_error']:
                print(f"    Error: {env_status['credentials_error']}")
                print("    Run: python diagnose_credentials_issue.py for detailed diagnosis")

        # Available modes
        print("\nAvailable Launch Modes:")
        print(f"  Simple Mode: {'✓' if env_status['simple_mode_available'] else '✗'}")
        print(f"  Orchestrated Mode: {'✓' if env_status['orchestrated_mode_available'] else '✗'}")
        print(f"  Paper Trading: {'✓' if env_status['paper_trading_available'] else '✗'}")

        print("=" * 50)

    async def launch_simple_mode(self):
        """Launch simple bot mode"""
        self.logger.info("Launching SIMPLE mode...")

        # Check credentials before launching
        env_status = self.check_environment()
        if not env_status['credentials_configured']:
            self.logger.error("Cannot launch bot: credentials not properly configured")
            print("\n" + "=" * 50)
            print("LAUNCH FAILED - CREDENTIAL ISSUE")
            print("=" * 50)
            if env_status['credentials_error']:
                print(f"Error: {env_status['credentials_error']}")
            print("\nTo fix this issue:")
            print("1. Run: python diagnose_credentials_issue.py")
            print("2. Follow the instructions to configure your .env file")
            print("3. Try launching the bot again")
            print("=" * 50)
            return False

        try:
            # Direct bot launch with proper error handling
            from src.config import load_config
            from src.core.bot import KrakenTradingBot

            # Load configuration
            config = load_config("config.json")
            if not config:
                self.logger.error("Failed to load configuration")
                return False

            self.logger.info("Initializing KrakenTradingBot...")
            bot = KrakenTradingBot()

            # Setup graceful shutdown
            import signal
            shutdown_event = asyncio.Event()

            def signal_handler(signum, frame):
                self.logger.info(f"Received signal {signum}, shutting down...")
                shutdown_event.set()

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Initialize and start bot
            self.logger.info("Initializing bot components...")
            await bot.initialize()

            self.logger.info("Starting trading operations...")
            self.logger.info("Press Ctrl+C to stop the bot")

            # Create tasks for bot operation and shutdown monitoring
            trading_task = asyncio.create_task(bot.run())
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            # Wait for either trading to complete or shutdown signal
            done, pending = await asyncio.wait(
                [trading_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()

            # Graceful shutdown
            self.logger.info("Shutting down bot...")
            await bot.shutdown()

            return True

        except Exception as e:
            self.logger.error(f"Simple mode launch failed: {e}")
            return False

    async def launch_orchestrated_mode(self):
        """Launch orchestrated mode"""
        self.logger.info("Launching ORCHESTRATED mode...")

        try:
            orchestrated_path = self.project_root / "main_orchestrated.py"
            if orchestrated_path.exists():
                import subprocess
                result = subprocess.run([
                    sys.executable, str(orchestrated_path)
                ], cwd=str(self.project_root))
                return result.returncode == 0
            else:
                self.logger.error("Orchestrated mode not available")
                return False

        except Exception as e:
            self.logger.error(f"Orchestrated mode launch failed: {e}")
            return False

    async def launch_paper_trading(self):
        """Launch paper trading mode"""
        self.logger.info("Launching PAPER TRADING mode...")

        try:
            paper_launcher_path = self.project_root / "launch_paper_trading.py"
            if paper_launcher_path.exists():
                import subprocess
                result = subprocess.run([
                    sys.executable, str(paper_launcher_path)
                ], cwd=str(self.project_root))
                return result.returncode == 0
            else:
                self.logger.error("Paper trading mode not available")
                return False

        except Exception as e:
            self.logger.error(f"Paper trading launch failed: {e}")
            return False

    async def run_tests(self):
        """Run component tests"""
        self.logger.info("Running component tests...")

        try:
            test_launcher_path = self.project_root / "simple_bot_launch.py"
            if test_launcher_path.exists():
                import subprocess
                result = subprocess.run([
                    sys.executable, str(test_launcher_path)
                ], cwd=str(self.project_root))
                return result.returncode == 0
            else:
                # Run basic component test
                print("Running basic component validation...")
                from src.utils.consolidated_nonce_manager import get_unified_nonce_manager

                nonce_manager = get_unified_nonce_manager()
                nonce = nonce_manager.get_nonce("test")
                print(f"✓ Nonce system working: {nonce}")

                print("✓ Basic components validated")
                return True

        except Exception as e:
            self.logger.error(f"Tests failed: {e}")
            return False

    def show_status(self):
        """Show current bot status"""
        self.logger.info("Checking bot status...")

        try:
            # Check if bot is running
            import psutil

            running_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any('bot' in str(cmd).lower() or 'trading' in str(cmd).lower() for cmd in cmdline):
                        if any('python' in str(cmd).lower() for cmd in cmdline):
                            running_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': ' '.join(cmdline[:3])  # First 3 args
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            print("\n" + "=" * 50)
            print("BOT STATUS CHECK")
            print("=" * 50)

            if running_processes:
                print("Running bot processes:")
                for proc in running_processes:
                    print(f"  PID {proc['pid']}: {proc['cmdline']}")
            else:
                print("No bot processes currently running")

            # Check for recent logs
            log_dirs = [
                Path("D:/trading_data/logs"),
                Path("logs"),
                self.project_root / "logs"
            ]

            recent_logs = []
            for log_dir in log_dirs:
                if log_dir.exists():
                    for log_file in log_dir.glob("*.log"):
                        try:
                            stat = log_file.stat()
                            recent_logs.append((log_file, stat.st_mtime))
                        except:
                            continue

            if recent_logs:
                recent_logs.sort(key=lambda x: x[1], reverse=True)
                print(f"\nMost recent log: {recent_logs[0][0]}")
                print(f"Last modified: {datetime.fromtimestamp(recent_logs[0][1])}")

            print("=" * 50)

        except ImportError:
            print("Status check requires psutil package")
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")

    def interactive_mode_selection(self, env_status: dict[str, Any]):
        """Interactive mode selection"""
        print("\n" + "=" * 50)
        print("SELECT LAUNCH MODE")
        print("=" * 50)

        options = []

        if env_status['simple_mode_available']:
            options.append(("1", "Simple Mode", "Basic bot launch with core features"))

        if env_status['orchestrated_mode_available']:
            options.append(("2", "Orchestrated Mode", "Full system with monitoring and diagnostics"))

        if env_status['paper_trading_available']:
            options.append(("3", "Paper Trading", "Safe trading simulation mode"))

        options.extend([
            ("4", "Component Tests", "Test core components and validate setup"),
            ("5", "Status Check", "Check if bot is currently running"),
            ("6", "Environment Info", "Show detailed environment information"),
            ("q", "Quit", "Exit launcher")
        ])

        for option_key, name, desc in options:
            print(f"  {option_key}. {name} - {desc}")

        print("=" * 50)

        while True:
            try:
                choice = input("Select option [1-6, q]: ").strip().lower()

                if choice == "q":
                    print("Exiting launcher...")
                    return None
                elif choice == "1" and env_status['simple_mode_available']:
                    return "simple"
                elif choice == "2" and env_status['orchestrated_mode_available']:
                    return "orchestrated"
                elif choice == "3" and env_status['paper_trading_available']:
                    return "paper"
                elif choice == "4":
                    return "test"
                elif choice == "5":
                    return "status"
                elif choice == "6":
                    return "info"
                else:
                    print("Invalid option. Please try again.")

            except KeyboardInterrupt:
                print("\nExiting launcher...")
                return None

    async def run(self, args):
        """Main execution method"""
        try:
            env_status = self.check_environment()

            # Handle command line arguments
            if args.status:
                self.show_status()
                return 0
            elif args.info:
                self.display_environment_status(env_status)
                return 0
            elif args.test:
                success = await self.run_tests()
                return 0 if success else 1
            elif args.simple:
                success = await self.launch_simple_mode()
                return 0 if success else 1
            elif args.orchestrated:
                success = await self.launch_orchestrated_mode()
                return 0 if success else 1
            elif args.paper:
                success = await self.launch_paper_trading()
                return 0 if success else 1

            # Interactive mode
            self.display_environment_status(env_status)

            mode = self.interactive_mode_selection(env_status)
            if mode is None:
                return 0

            if mode == "simple":
                success = await self.launch_simple_mode()
                return 0 if success else 1
            elif mode == "orchestrated":
                success = await self.launch_orchestrated_mode()
                return 0 if success else 1
            elif mode == "paper":
                success = await self.launch_paper_trading()
                return 0 if success else 1
            elif mode == "test":
                success = await self.run_tests()
                return 0 if success else 1
            elif mode == "status":
                self.show_status()
                return 0
            elif mode == "info":
                self.display_environment_status(env_status)
                return 0

            return 0

        except KeyboardInterrupt:
            print("\nLauncher interrupted by user")
            return 130
        except Exception as e:
            self.logger.error(f"Launch failed: {e}")
            print(f"CRITICAL ERROR: {e}")
            return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Unified Crypto Trading Bot Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive mode selection
  python main.py --simple           # Launch simple bot
  python main.py --orchestrated     # Launch with full orchestration
  python main.py --paper            # Launch paper trading mode
  python main.py --test             # Run component tests
  python main.py --status           # Check bot status
  python main.py --info             # Show environment info

For detailed help on any mode, add --help after the mode.
        """
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--simple", action="store_true",
                           help="Launch simple bot mode")
    mode_group.add_argument("--orchestrated", action="store_true",
                           help="Launch orchestrated mode with full monitoring")
    mode_group.add_argument("--paper", action="store_true",
                           help="Launch paper trading mode (safe simulation)")
    mode_group.add_argument("--test", action="store_true",
                           help="Run component tests only")
    mode_group.add_argument("--status", action="store_true",
                           help="Check current bot status")
    mode_group.add_argument("--info", action="store_true",
                           help="Show environment information")

    # Configuration options
    parser.add_argument("--config", type=str, default="config.json",
                       help="Configuration file path (default: config.json)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true",
                       help="Validate configuration without launching")

    args = parser.parse_args()

    # Create and run launcher
    launcher = UnifiedLauncher()

    try:
        exit_code = asyncio.run(launcher.run(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nLauncher interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Launcher failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
