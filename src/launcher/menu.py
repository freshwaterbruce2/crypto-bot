"""Interactive menu helpers for the launcher."""

from __future__ import annotations

from typing import Any


def interactive_mode_selection(env_status: dict[str, Any]) -> str | None:
    """Show menu and return selected mode."""

    print("\n" + "=" * 50)
    print("SELECT LAUNCH MODE")
    print("=" * 50)

    options: list[tuple[str, str, str]] = []
    if env_status.get("simple_mode_available"):
        options.append(("1", "Simple Mode", "Basic bot launch with core features"))
    if env_status.get("orchestrated_mode_available"):
        options.append(("2", "Orchestrated Mode", "Full system with monitoring and diagnostics"))
    if env_status.get("paper_trading_available"):
        options.append(("3", "Paper Trading", "Safe trading simulation mode"))
    options.extend(
        [
            ("4", "Component Tests", "Test core components and validate setup"),
            ("5", "Status Check", "Check if bot is currently running"),
            ("6", "Environment Info", "Show detailed environment information"),
            ("q", "Quit", "Exit launcher"),
        ]
    )

    for option_key, name, desc in options:
        print(f"  {option_key}. {name} - {desc}")
    print("=" * 50)

    while True:
        try:
            choice = input("Select option [1-6, q]: ").strip().lower()
            if choice == "q":
                print("Exiting launcher...")
                return None
            if choice == "1" and env_status.get("simple_mode_available"):
                return "simple"
            if choice == "2" and env_status.get("orchestrated_mode_available"):
                return "orchestrated"
            if choice == "3" and env_status.get("paper_trading_available"):
                return "paper"
            if choice == "4":
                return "test"
            if choice == "5":
                return "status"
            if choice == "6":
                return "info"
            print("Invalid option. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting launcher...")
            return None
