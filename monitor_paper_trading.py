#!/usr/bin/env python3
"""
Paper Trading Monitor
Real-time monitoring and reporting for paper trading operations
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class PaperTradingMonitor:
    """Real-time monitor for paper trading performance and health"""
    
    def __init__(self, monitoring_interval: int = 300):
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "paper_trading_data"
        self.monitoring_interval = monitoring_interval
        self.start_time = datetime.now()
        self.logger = None
        self.monitoring_active = False
        
    def setup_logging(self):
        """Setup logging for monitoring"""
        log_dir = Path("D:/trading_data/logs/paper_trading")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_dir / "paper_trading_monitor.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_safety_verification(self) -> Optional[Dict[str, Any]]:
        """Load safety verification data"""
        try:
            safety_file = self.data_dir / "safety_verification.json"
            if safety_file.exists():
                with open(safety_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading safety verification: {e}")
            return None
    
    def load_performance_data(self) -> Optional[Dict[str, Any]]:
        """Load current performance data"""
        try:
            perf_file = self.data_dir / "paper_performance.json"
            if perf_file.exists():
                with open(perf_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading performance data: {e}")
            return None
    
    def load_current_status(self) -> Optional[Dict[str, Any]]:
        """Load current bot status"""
        try:
            status_file = self.data_dir / "current_status.json"
            if status_file.exists():
                with open(status_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading current status: {e}")
            return None
    
    def check_safety_status(self) -> Dict[str, Any]:
        """Check safety status and paper trading mode"""
        safety_data = self.load_safety_verification()
        
        if not safety_data:
            return {
                "status": "ERROR",
                "message": "Safety verification file not found",
                "paper_mode_verified": False
            }
        
        paper_mode = safety_data.get("paper_trading_mode", False)
        live_disabled = safety_data.get("live_trading_disabled", False)
        
        if paper_mode and live_disabled:
            return {
                "status": "SAFE",
                "message": "Paper trading mode confirmed",
                "paper_mode_verified": True,
                "verification_time": safety_data.get("safety_verification_time")
            }
        else:
            return {
                "status": "DANGER",
                "message": "Safety verification failed",
                "paper_mode_verified": False
            }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze current performance metrics"""
        perf_data = self.load_performance_data()
        
        if not perf_data:
            return {
                "status": "NO_DATA",
                "message": "Performance data not available"
            }
        
        # Calculate key metrics
        starting_balance = perf_data.get("starting_balance", 150.0)
        current_balance = perf_data.get("current_balance", starting_balance)
        total_trades = perf_data.get("total_trades", 0)
        winning_trades = perf_data.get("winning_trades", 0)
        losing_trades = perf_data.get("losing_trades", 0)
        
        # Calculate derived metrics
        total_pnl = current_balance - starting_balance
        pnl_percentage = (total_pnl / starting_balance) * 100 if starting_balance > 0 else 0
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Determine status
        status = "HEALTHY"
        if total_pnl < -20:  # More than $20 loss
            status = "WARNING"
        if total_pnl < -30:  # Circuit breaker level
            status = "CRITICAL"
        
        return {
            "status": status,
            "starting_balance": starting_balance,
            "current_balance": current_balance,
            "total_pnl": total_pnl,
            "pnl_percentage": pnl_percentage,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "last_updated": perf_data.get("last_updated")
        }
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        status_data = self.load_current_status()
        
        if not status_data:
            return {
                "status": "UNKNOWN",
                "message": "System status data not available",
                "uptime_hours": 0
            }
        
        uptime_hours = status_data.get("uptime_hours", 0)
        health_status = status_data.get("health_status", "UNKNOWN")
        
        # Check if data is stale
        last_update = status_data.get("timestamp")
        if last_update:
            last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            time_since_update = datetime.now() - last_update_time.replace(tzinfo=None)
            
            if time_since_update > timedelta(minutes=10):
                return {
                    "status": "STALE",
                    "message": f"No updates for {time_since_update}",
                    "uptime_hours": uptime_hours,
                    "last_update": last_update
                }
        
        return {
            "status": health_status,
            "message": "System operating normally",
            "uptime_hours": uptime_hours,
            "last_update": last_update,
            "paper_mode_verified": status_data.get("paper_mode_verified", False)
        }
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        report_time = datetime.now()
        
        # Collect all status information
        safety_status = self.check_safety_status()
        performance_analysis = self.analyze_performance()
        system_health = self.check_system_health()
        
        # Calculate monitoring duration
        monitoring_duration = report_time - self.start_time
        
        report = {
            "report_timestamp": report_time.isoformat(),
            "monitoring_start_time": self.start_time.isoformat(),
            "monitoring_duration_hours": monitoring_duration.total_seconds() / 3600,
            "safety_status": safety_status,
            "performance_analysis": performance_analysis,
            "system_health": system_health,
            "alerts": [],
            "recommendations": []
        }
        
        # Generate alerts based on status
        if safety_status["status"] != "SAFE":
            report["alerts"].append({
                "type": "SAFETY",
                "severity": "CRITICAL",
                "message": "Paper trading safety verification failed"
            })
        
        if performance_analysis.get("status") == "CRITICAL":
            report["alerts"].append({
                "type": "PERFORMANCE",
                "severity": "CRITICAL",
                "message": f"Large loss detected: ${performance_analysis.get('total_pnl', 0):.2f}"
            })
        elif performance_analysis.get("status") == "WARNING":
            report["alerts"].append({
                "type": "PERFORMANCE",
                "severity": "WARNING",
                "message": f"Loss warning: ${performance_analysis.get('total_pnl', 0):.2f}"
            })
        
        if system_health.get("status") == "STALE":
            report["alerts"].append({
                "type": "SYSTEM",
                "severity": "WARNING",
                "message": "System status data is stale"
            })
        
        # Generate recommendations
        if len(report["alerts"]) == 0:
            report["recommendations"].append("System operating normally - continue monitoring")
        else:
            report["recommendations"].append("Review alerts and take appropriate action")
        
        if performance_analysis.get("total_trades", 0) > 0:
            win_rate = performance_analysis.get("win_rate", 0)
            if win_rate < 50:
                report["recommendations"].append(f"Win rate ({win_rate:.1f}%) below 50% - consider strategy adjustment")
        
        return report
    
    def save_report(self, report: Dict[str, Any]):
        """Save monitoring report to file"""
        try:
            # Save to reports directory
            reports_dir = self.data_dir / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"monitoring_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Also save as latest report
            latest_file = reports_dir / "latest_monitoring_report.json"
            with open(latest_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Monitoring report saved: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
    
    def display_status_summary(self, report: Dict[str, Any]):
        """Display formatted status summary"""
        print("\n" + "=" * 60)
        print("🧪 PAPER TRADING MONITOR - STATUS SUMMARY")
        print("=" * 60)
        print(f"Report Time: {report['report_timestamp']}")
        print(f"Monitoring Duration: {report['monitoring_duration_hours']:.1f} hours")
        
        # Safety Status
        safety = report['safety_status']
        safety_icon = "✅" if safety['status'] == 'SAFE' else "❌"
        print(f"\n🔒 Safety Status: {safety_icon} {safety['status']}")
        print(f"   Paper Mode Verified: {safety.get('paper_mode_verified', False)}")
        
        # Performance Analysis
        perf = report['performance_analysis']
        if perf.get('status') != 'NO_DATA':
            perf_icon = "✅" if perf['status'] == 'HEALTHY' else "⚠️" if perf['status'] == 'WARNING' else "🚨"
            print(f"\n📊 Performance: {perf_icon} {perf['status']}")
            print(f"   Current Balance: ${perf.get('current_balance', 0):.2f}")
            print(f"   Total P&L: ${perf.get('total_pnl', 0):.2f} ({perf.get('pnl_percentage', 0):.2f}%)")
            print(f"   Total Trades: {perf.get('total_trades', 0)}")
            print(f"   Win Rate: {perf.get('win_rate', 0):.1f}%")
        else:
            print(f"\n📊 Performance: ⚪ NO DATA")
        
        # System Health
        health = report['system_health']
        health_icon = "✅" if health['status'] in ['HEALTHY', 'RUNNING'] else "⚠️"
        print(f"\n🖥️ System Health: {health_icon} {health['status']}")
        print(f"   Uptime: {health.get('uptime_hours', 0):.1f} hours")
        
        # Alerts
        alerts = report.get('alerts', [])
        if alerts:
            print(f"\n🚨 Active Alerts ({len(alerts)}):")
            for alert in alerts:
                severity_icon = "🚨" if alert['severity'] == 'CRITICAL' else "⚠️"
                print(f"   {severity_icon} {alert['type']}: {alert['message']}")
        else:
            print(f"\n🚨 Active Alerts: None")
        
        # Recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                print(f"   • {rec}")
        
        print("=" * 60)
    
    async def continuous_monitoring(self):
        """Run continuous monitoring loop"""
        self.monitoring_active = True
        self.logger.info(f"Starting continuous monitoring (interval: {self.monitoring_interval}s)")
        
        try:
            while self.monitoring_active:
                # Generate and save report
                report = self.generate_monitoring_report()
                self.save_report(report)
                
                # Display status if in interactive mode
                if sys.stdout.isatty():
                    self.display_status_summary(report)
                
                # Check for critical alerts
                critical_alerts = [a for a in report.get('alerts', []) if a.get('severity') == 'CRITICAL']
                if critical_alerts:
                    self.logger.critical(f"CRITICAL ALERTS DETECTED: {len(critical_alerts)} alerts")
                    for alert in critical_alerts:
                        self.logger.critical(f"  {alert['type']}: {alert['message']}")
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            self.monitoring_active = False
    
    def run_single_check(self):
        """Run a single monitoring check and display results"""
        print("🧪 PAPER TRADING STATUS CHECK")
        print("=" * 50)
        
        report = self.generate_monitoring_report()
        self.save_report(report)
        self.display_status_summary(report)
        
        return report
    
    async def run_monitoring(self, continuous: bool = False):
        """Run monitoring (single check or continuous)"""
        if continuous:
            await self.continuous_monitoring()
        else:
            self.run_single_check()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Paper Trading Monitor")
    parser.add_argument("--continuous", action="store_true",
                       help="Run continuous monitoring")
    parser.add_argument("--interval", type=int, default=300,
                       help="Monitoring interval in seconds (default: 300)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = PaperTradingMonitor(monitoring_interval=args.interval)
    monitor.setup_logging()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        asyncio.run(monitor.run_monitoring(continuous=args.continuous))
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"Monitoring failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()