"""Launcher mode helpers."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


async def launch_simple_mode(logger) -> bool:
    """Launch simple bot mode."""

    from src.launcher.environment import check_environment

    env_status = check_environment(Path(__file__).resolve().parents[2])
    if not env_status["credentials_configured"]:
        logger.error("Cannot launch bot: credentials not properly configured")
        print("\n" + "=" * 50)
        print("LAUNCH FAILED - CREDENTIAL ISSUE")
        print("=" * 50)
        if env_status["credentials_error"]:
            print(f"Error: {env_status['credentials_error']}")
        print("\nTo fix this issue:")
        print("1. Check your .env file has KRAKEN_KEY and KRAKEN_SECRET")
        print("2. Make sure they are real API keys, not placeholder values")
        print("3. Try launching the bot again")
        print("=" * 50)
        return False

    try:
        from simple_shib_bot import SimpleShibBot

        logger.info("Starting Simple SHIB/USDT Trading Bot...")
        bot = SimpleShibBot()
        if hasattr(bot, "start"):
            result = bot.start()
            if hasattr(result, "__await__"):
                await result  # type: ignore[func-returns-value]
                return True
            return bool(result)
        return False
    except Exception as exc:  # pragma: no cover - launcher only
        logger.error(f"Simple mode launch failed: {exc}")
        return False


async def _run_subprocess(target: Path, logger) -> bool:
    try:
        result = subprocess.run([sys.executable, str(target)], cwd=str(target.parent))
        return result.returncode == 0
    except Exception as exc:  # pragma: no cover - launcher only
        logger.error(f"Process {target} failed: {exc}")
        return False


async def launch_orchestrated_mode(project_root: Path, logger) -> bool:
    """Launch orchestrated mode."""

    orchestrated_path = project_root / "main_orchestrated.py"
    if orchestrated_path.exists():
        return await _run_subprocess(orchestrated_path, logger)
    logger.error("Orchestrated mode not available")
    return False


async def launch_paper_trading(project_root: Path, logger) -> bool:
    """Launch paper trading mode."""

    paper_launcher_path = project_root / "launch_paper_trading.py"
    if paper_launcher_path.exists():
        return await _run_subprocess(paper_launcher_path, logger)
    logger.error("Paper trading mode not available")
    return False


async def run_tests(project_root: Path, logger) -> bool:
    """Run component tests."""

    test_launcher_path = project_root / "simple_bot_launch.py"
    if test_launcher_path.exists():
        return await _run_subprocess(test_launcher_path, logger)

    try:
        from src.utils.consolidated_nonce_manager import get_unified_nonce_manager

        nonce_manager = get_unified_nonce_manager()
        nonce = nonce_manager.get_nonce("test")
        print(f"\u2713 Nonce system working: {nonce}")
        print("\u2713 Basic components validated")
        return True
    except Exception as exc:  # pragma: no cover - launcher only
        logger.error(f"Tests failed: {exc}")
        return False


def show_status(project_root: Path, logger) -> None:
    """Show current bot status."""

    try:
        import psutil

        running_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info["cmdline"]
                if cmdline and any("bot" in str(cmd).lower() or "trading" in str(cmd).lower() for cmd in cmdline):
                    if any("python" in str(cmd).lower() for cmd in cmdline):
                        running_processes.append({
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cmdline": " ".join(cmdline[:3]),
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

        log_dirs = [Path("D:/trading_data/logs"), Path("logs"), project_root / "logs"]
        recent_logs = []
        for log_dir in log_dirs:
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        stat = log_file.stat()
                        recent_logs.append((log_file, stat.st_mtime))
                    except OSError as exc:
                        logger.debug(f"Could not stat log file {log_file}: {exc}")
                        continue

        if recent_logs:
            recent_logs.sort(key=lambda item: item[1], reverse=True)
            print(f"\nMost recent log: {recent_logs[0][0]}")
            print(f"Last modified: {datetime.fromtimestamp(recent_logs[0][1])}")
        print("=" * 50)
    except ImportError:
        print("Status check requires psutil package")
    except Exception as exc:  # pragma: no cover - launcher only
        logger.error(f"Status check failed: {exc}")
