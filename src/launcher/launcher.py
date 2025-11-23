"""Unified launcher implementation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from src.launcher import menu
from src.launcher.cli import build_parser
from src.launcher.environment import (
    check_environment,
    configure_windows_bridge,
    display_environment_status,
    setup_logging,
)
from src.launcher.modes import (
    launch_orchestrated_mode,
    launch_paper_trading,
    launch_simple_mode,
    run_tests,
    show_status,
)


class UnifiedLauncher:
    """Unified launcher for all bot modes."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        configure_windows_bridge()
        self.logger = setup_logging(self.project_root)

    async def run(self, args) -> int:
        env_status = check_environment(self.project_root)
        if args.status:
            show_status(self.project_root, self.logger)
            return 0
        if args.info:
            display_environment_status(env_status, self.project_root)
            return 0
        if args.test:
            return 0 if await run_tests(self.project_root, self.logger) else 1
        if args.simple:
            return 0 if await launch_simple_mode(self.logger) else 1
        if args.orchestrated:
            return 0 if await launch_orchestrated_mode(self.project_root, self.logger) else 1
        if args.paper:
            return 0 if await launch_paper_trading(self.project_root, self.logger) else 1

        display_environment_status(env_status, self.project_root)
        mode = menu.interactive_mode_selection(env_status)
        if mode is None:
            return 0
        if mode == "simple":
            return 0 if await launch_simple_mode(self.logger) else 1
        if mode == "orchestrated":
            return 0 if await launch_orchestrated_mode(self.project_root, self.logger) else 1
        if mode == "paper":
            return 0 if await launch_paper_trading(self.project_root, self.logger) else 1
        if mode == "test":
            return 0 if await run_tests(self.project_root, self.logger) else 1
        if mode == "status":
            show_status(self.project_root, self.logger)
            return 0
        if mode == "info":
            display_environment_status(env_status, self.project_root)
            return 0
        return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    launcher = UnifiedLauncher()
    try:
        exit_code = asyncio.run(launcher.run(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nLauncher interrupted")
        sys.exit(130)
    except Exception as exc:  # pragma: no cover - launcher entry point
        print(f"Launcher failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
