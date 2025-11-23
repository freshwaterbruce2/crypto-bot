"""Environment setup and validation helpers for the launcher."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.utils.custom_logging import configure_logging

load_dotenv()


def configure_windows_bridge() -> None:
    """Configure Windows-specific credential bridging and event loop."""

    if platform.system() == "Windows":
        try:
            has_system_creds = os.environ.get("KRAKEN_KEY") or os.environ.get("KRAKEN_API_KEY")
            if has_system_creds and not os.getenv("KRAKEN_KEY"):
                from fix_windows_credentials import fix_credential_loading

                if fix_credential_loading():
                    print("\u2713 Windows credentials synchronized from system environment")
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Note: Could not sync Windows credentials: {exc}")
    else:
        try:
            from src.utils.windows_env_bridge import WSL_ENVIRONMENT, setup_kraken_credentials

            if WSL_ENVIRONMENT:
                print("Detected WSL environment - setting up Windows environment bridge...")
                bridge_success = setup_kraken_credentials()
                if bridge_success:
                    print("\u2713 Windows environment bridge setup successful")
                else:
                    print("\u26a0 Windows environment bridge setup failed - will try other credential sources")
        except ImportError:
            pass
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Warning: Windows environment bridge setup error: {exc}")

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def setup_logging(project_root: Path) -> logging.Logger:
    """Configure logging for the launcher."""

    try:
        logger = configure_logging()
        logger.info("=" * 60)
        logger.info("CRYPTO TRADING BOT - UNIFIED LAUNCHER")
        logger.info("=" * 60)
        logger.info(f"Launch time: {datetime.now()}")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        return logger
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"WARNING: Failed to setup logging: {exc}")
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)


def _credentials_configured() -> tuple[bool, str | None]:
    try:
        from src.auth.credential_manager import get_credential_status

        credential_status = get_credential_status()
        has_valid_unified = (
            credential_status["unified_credentials"]["found"]
            and credential_status["unified_credentials"]["valid"]
        )
        has_valid_generic = (
            credential_status["generic_credentials"]["found"]
            and credential_status["generic_credentials"]["valid"]
        )
        if has_valid_unified or has_valid_generic:
            from src.auth.credential_manager import get_kraken_credentials

            api_key, private_key = get_kraken_credentials()
            placeholder_values = {
                "YOUR_NEW_API_KEY_HERE",
                "YOUR_NEW_API_SECRET_HERE",
                "YOUR_API_KEY_HERE",
                "YOUR_API_SECRET_HERE",
            }
            if api_key and private_key and api_key not in placeholder_values and private_key not in placeholder_values:
                return True, None
            return False, "Placeholder values found in .env file - please configure with real API keys"
        return False, "No valid credentials found in environment variables or .env file"
    except Exception as exc:  # pragma: no cover - defensive logging
        return False, f"Error checking credentials: {exc}"


def check_environment(project_root: Path) -> dict[str, Any]:
    """Check environment and dependencies."""

    env_status: dict[str, Any] = {
        "python_version": sys.version,
        "platform": sys.platform,
        "project_root_exists": project_root.exists(),
        "config_exists": (project_root / "config.json").exists(),
        "env_file_exists": (project_root / ".env").exists(),
        "src_directory_exists": (project_root / "src").exists(),
        "requirements_exist": (project_root / "requirements.txt").exists(),
        "paper_trading_available": False,
        "orchestrated_mode_available": False,
        "simple_mode_available": False,
        "credentials_configured": False,
        "credentials_error": None,
    }

    env_status["credentials_configured"], env_status["credentials_error"] = _credentials_configured()

    try:
        from src.paper_trading.integration import get_paper_integration

        env_status["paper_trading_available"] = True
    except ImportError:
        pass

    if (project_root / "main_orchestrated.py").exists():
        env_status["orchestrated_mode_available"] = True

    try:
        from src.core.bot import KrakenTradingBot  # noqa: F401

        env_status["simple_mode_available"] = True
    except ImportError:
        pass

    return env_status


def display_environment_status(env_status: dict[str, Any], project_root: Path) -> None:
    """Display current environment status."""

    print("\n" + "=" * 50)
    print("ENVIRONMENT STATUS")
    print("=" * 50)
    print(f"Python Version: {env_status['python_version'].split()[0]}")
    print(f"Platform: {env_status['platform']}")
    print(f"Project Root: {project_root}")
    config_mark = "\u2713" if env_status["config_exists"] else "\u2717"
    env_mark = "\u2713" if env_status["env_file_exists"] else "\u2717"
    src_mark = "\u2713" if env_status["src_directory_exists"] else "\u2717"
    req_mark = "\u2713" if env_status["requirements_exist"] else "\u2717"
    print("\nCore Files:")
    print(f"  Config file: {config_mark}")
    print(f"  Environment file: {env_mark}")
    print(f"  Source directory: {src_mark}")
    print(f"  Requirements: {req_mark}")
    print("\nCredential Configuration:")
    if env_status["credentials_configured"]:
        print("  API Credentials: \u2713 Configured and valid")
    else:
        print("  API Credentials: \u2717 Not configured or invalid")
        if env_status["credentials_error"]:
            print(f"    Error: {env_status['credentials_error']}")
            print("    Run: python diagnose_credentials_issue.py for detailed diagnosis")
    simple_mark = "\u2713" if env_status["simple_mode_available"] else "\u2717"
    orchestrated_mark = "\u2713" if env_status["orchestrated_mode_available"] else "\u2717"
    paper_mark = "\u2713" if env_status["paper_trading_available"] else "\u2717"
    print("\nAvailable Launch Modes:")
    print(f"  Simple Mode: {simple_mark}")
    print(f"  Orchestrated Mode: {orchestrated_mark}")
    print(f"  Paper Trading: {paper_mark}")
    print("=" * 50)
