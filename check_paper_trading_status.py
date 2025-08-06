#!/usr/bin/env python3
"""
Quick Paper Trading Status Checker
Simple script to check current paper trading status
"""

import json
from datetime import datetime
from pathlib import Path


def check_paper_trading_status():
    """Check current paper trading status"""
    print("🧪 PAPER TRADING STATUS CHECK")
    print("=" * 50)

    project_root = Path(__file__).parent
    data_dir = project_root / "paper_trading_data"

    # Check if paper trading is running
    if not data_dir.exists():
        print("❌ Paper trading data directory not found")
        print("   The bot may not have been started yet")
        print("\n💡 To start paper trading:")
        print("   Windows: LAUNCH_PAPER_TRADING.bat")
        print("   Linux/macOS: python launch_paper_trading.py")
        return False

    print(f"✅ Data directory found: {data_dir}")

    # Check safety verification
    safety_file = data_dir / "safety_verification.json"
    if safety_file.exists():
        try:
            with open(safety_file) as f:
                safety_data = json.load(f)

            print("✅ Safety verification file found")
            print(f"   Paper mode verified: {safety_data.get('paper_trading_mode', False)}")
            print(f"   Live trading disabled: {safety_data.get('live_trading_disabled', False)}")
            print(f"   Verified at: {safety_data.get('safety_verification_time', 'Unknown')}")

            if not safety_data.get('paper_trading_mode', False):
                print("⚠️  WARNING: Paper trading mode not confirmed in safety file")

        except Exception as e:
            print(f"⚠️  Error reading safety file: {e}")
    else:
        print("❌ Safety verification file not found")
        print("   This may indicate the bot is not running properly")

    # Check performance data
    perf_file = data_dir / "paper_performance.json"
    if perf_file.exists():
        try:
            with open(perf_file) as f:
                perf_data = json.load(f)

            print("✅ Performance data file found")
            print(f"   Total trades: {perf_data.get('total_trades', 0)}")
            print(f"   Current balance: ${perf_data.get('current_balance', 0):.2f}")
            print(f"   Total P&L: ${perf_data.get('total_pnl', 0):+.2f}")

            winning_trades = perf_data.get('winning_trades', 0)
            total_trades = perf_data.get('total_trades', 0)
            if total_trades > 0:
                win_rate = (winning_trades / total_trades) * 100
                print(f"   Win rate: {win_rate:.1f}%")

            last_updated = perf_data.get('last_updated', 'Unknown')
            print(f"   Last updated: {last_updated}")

        except Exception as e:
            print(f"⚠️  Error reading performance file: {e}")
    else:
        print("❌ Performance data file not found")
        print("   No trades may have been executed yet")

    # Check current status
    status_file = data_dir / "current_status.json"
    if status_file.exists():
        try:
            with open(status_file) as f:
                status_data = json.load(f)

            print("✅ Current status file found")
            print(f"   Bot health: {status_data.get('health_status', 'Unknown')}")
            print(f"   Uptime: {status_data.get('uptime_hours', 0):.1f} hours")
            print(f"   Paper mode verified: {status_data.get('paper_mode_verified', False)}")

            # Check if status is recent
            timestamp = status_data.get('timestamp')
            if timestamp:
                try:
                    last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_diff = datetime.now() - last_update.replace(tzinfo=None)
                    if time_diff.total_seconds() > 600:  # 10 minutes
                        print(f"⚠️  Status is {time_diff} old - bot may not be running")
                    else:
                        print(f"   Status updated: {time_diff} ago")
                except Exception:
                    print(f"   Last status update: {timestamp}")

        except Exception as e:
            print(f"⚠️  Error reading status file: {e}")
    else:
        print("❌ Current status file not found")
        print("   Bot may not be actively running")

    # Check log files
    log_dirs = [
        data_dir / "logs",
        Path("D:/trading_data/logs/paper_trading")
    ]

    for log_dir in log_dirs:
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            if log_files:
                print(f"✅ Log files found in {log_dir}: {len(log_files)} files")
                # Check most recent log file
                if log_files:
                    newest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                    size_mb = newest_log.stat().st_size / (1024 * 1024)
                    print(f"   Latest log: {newest_log.name} ({size_mb:.1f} MB)")
                break
    else:
        print("❌ No log files found")

    # Check reports
    reports_dir = data_dir / "reports"
    if reports_dir.exists():
        report_files = list(reports_dir.glob("*.json"))
        if report_files:
            print(f"✅ Report files found: {len(report_files)} reports")
            # Check latest report
            if report_files:
                newest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                print(f"   Latest report: {newest_report.name}")
        else:
            print("⚠️  Reports directory exists but no reports found")
    else:
        print("❌ Reports directory not found")

    print("=" * 50)

    # Summary and recommendations
    print("\n📋 STATUS SUMMARY:")

    if safety_file.exists() and perf_file.exists():
        print("✅ Paper trading appears to be running")
        print("✅ Safety verification in place")
        print("✅ Performance tracking active")

        if status_file.exists():
            print("✅ Real-time monitoring active")
        else:
            print("⚠️  Real-time monitoring may not be active")

        print("\n💡 NEXT STEPS:")
        print("• Use 'python monitor_paper_trading.py' for detailed status")
        print("• Check reports in paper_trading_data/reports/")
        print("• Monitor logs for any issues")
        print("• Let the bot run for 3-5 days for complete testing")

    else:
        print("❌ Paper trading does not appear to be running properly")
        print("\n💡 TROUBLESHOOTING:")
        print("• Run 'python validate_paper_trading_setup.py' to check setup")
        print("• Launch with 'python launch_paper_trading.py'")
        print("• Check logs for error messages")
        print("• Verify configuration files exist")

    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        check_paper_trading_status()
    except KeyboardInterrupt:
        print("\nStatus check interrupted by user")
    except Exception as e:
        print(f"\nError during status check: {e}")
        import traceback
        traceback.print_exc()
