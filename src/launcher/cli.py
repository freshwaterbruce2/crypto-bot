"""CLI parsing helpers for the unified launcher."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
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
        """,
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--simple", action="store_true", help="Launch simple bot mode")
    mode_group.add_argument(
        "--orchestrated", action="store_true", help="Launch orchestrated mode with full monitoring"
    )
    mode_group.add_argument(
        "--paper", action="store_true", help="Launch paper trading mode (safe simulation)"
    )
    mode_group.add_argument("--test", action="store_true", help="Run component tests only")
    mode_group.add_argument("--status", action="store_true", help="Check current bot status")
    mode_group.add_argument("--info", action="store_true", help="Show environment information")

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Configuration file path (default: config.json)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without launching")
    return parser
