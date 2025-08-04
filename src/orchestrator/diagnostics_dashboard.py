"""
System Diagnostics Dashboard

Provides real-time monitoring and diagnostics for the orchestrated system.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

from .system_orchestrator import SystemOrchestrator
from .health_monitor import HealthStatus

logger = logging.getLogger(__name__)


class DiagnosticsDashboard:
    """Real-time diagnostics dashboard for system monitoring"""
    
    def __init__(self, orchestrator: SystemOrchestrator):
        self.orchestrator = orchestrator
        self.console = Console()
        self.refresh_interval = 1.0
        self.running = False
        
    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="status", size=10),
            Layout(name="components", size=15),
            Layout(name="metrics")
        )
        
        layout["right"].split_column(
            Layout(name="health", size=20),
            Layout(name="alerts")
        )
        
        return layout
        
    def generate_header(self) -> Panel:
        """Generate header panel"""
        status = self.orchestrator.get_status()
        
        health_color = {
            HealthStatus.HEALTHY: "green",
            HealthStatus.DEGRADED: "yellow",
            HealthStatus.UNHEALTHY: "red",
            HealthStatus.CRITICAL: "red bold",
            HealthStatus.UNKNOWN: "dim"
        }
        
        health_status = self.orchestrator.health.get_system_status()
        
        header_text = Text()
        header_text.append("🚀 Crypto Trading Bot System Dashboard\n", style="bold cyan")
        header_text.append(f"Status: ", style="white")
        header_text.append(
            "RUNNING" if status['running'] else "STOPPED",
            style="green bold" if status['running'] else "red bold"
        )
        header_text.append(" | Health: ", style="white")
        header_text.append(
            health_status.value.upper(),
            style=health_color.get(health_status, "white")
        )
        header_text.append(f" | Uptime: {self._format_duration(status['uptime'])}", style="white")
        
        return Panel(header_text, style="bold blue")
        
    def generate_status(self) -> Panel:
        """Generate system status panel"""
        status = self.orchestrator.get_status()
        config = self.orchestrator.config
        
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Initialized", "✓" if status['initialized'] else "✗")
        table.add_row("Running", "✓" if status['running'] else "✗")
        table.add_row("Startup Time", f"{status['metrics'].get('startup_time', 0):.2f}s")
        table.add_row("Total Errors", str(status['metrics'].get('errors', 0)))
        table.add_row("Config Mode", config.get('system.debug', False) and "DEBUG" or "PRODUCTION")
        table.add_row("Trading Pairs", str(len(config.get('trading.pairs', []))))
        
        return Panel(table, title="System Status", style="green")
        
    def generate_components(self) -> Panel:
        """Generate components status panel"""
        services = self.orchestrator.injector.get_all_services()
        
        table = Table(show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Lifetime", style="yellow")
        
        for name, info in services.items():
            if info:
                status_icon = "✓" if info['instance_created'] else "○"
                status_color = "green" if info['instance_created'] else "dim"
                
                table.add_row(
                    name,
                    Text(status_icon, style=status_color),
                    info['lifetime']
                )
                
        return Panel(table, title="Components", style="blue")
        
    def generate_metrics(self) -> Panel:
        """Generate performance metrics panel"""
        # Get various metrics
        table = Table(show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="yellow")
        
        # System metrics from health monitor
        system_health = self.orchestrator.health.get_component_health('system')
        if system_health:
            for metric_name, metric in system_health.metrics.items():
                status_icon = "✓" if metric.get_status() == HealthStatus.HEALTHY else "⚠"
                status_color = "green" if metric.get_status() == HealthStatus.HEALTHY else "yellow"
                
                table.add_row(
                    metric_name.replace('_', ' ').title(),
                    f"{metric.value:.1f}{metric.unit}",
                    Text(status_icon, style=status_color)
                )
                
        return Panel(table, title="Performance Metrics", style="yellow")
        
    def generate_health(self) -> Panel:
        """Generate health status panel"""
        health_data = self.orchestrator.health.get_all_health()
        
        table = Table(show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Last Check", style="yellow")
        table.add_column("Errors", style="red")
        
        status_colors = {
            HealthStatus.HEALTHY: "green",
            HealthStatus.DEGRADED: "yellow",
            HealthStatus.UNHEALTHY: "red",
            HealthStatus.CRITICAL: "red bold",
            HealthStatus.UNKNOWN: "dim"
        }
        
        for name, health in health_data.items():
            table.add_row(
                name,
                Text(health.status.value, style=status_colors.get(health.status, "white")),
                self._format_time_ago(health.last_check),
                str(health.error_count) if health.error_count > 0 else "-"
            )
            
        return Panel(table, title="Health Monitor", style="magenta")
        
    def generate_alerts(self) -> Panel:
        """Generate recent alerts panel"""
        alerts = self.orchestrator.health.get_recent_alerts(10)
        
        if not alerts:
            return Panel("No recent alerts", title="Alerts", style="green")
            
        table = Table(show_header=True)
        table.add_column("Time", style="yellow")
        table.add_column("Level", style="white")
        table.add_column("Component", style="cyan")
        table.add_column("Message", style="white")
        
        level_colors = {
            'info': "blue",
            'warning': "yellow",
            'error': "red",
            'critical': "red bold"
        }
        
        for alert in reversed(alerts):
            table.add_row(
                self._format_time_ago(alert.timestamp),
                Text(alert.level.value.upper(), style=level_colors.get(alert.level.value, "white")),
                alert.component,
                alert.message[:50] + "..." if len(alert.message) > 50 else alert.message
            )
            
        return Panel(table, title="Recent Alerts", style="red")
        
    def generate_footer(self) -> Panel:
        """Generate footer panel"""
        text = Text()
        text.append("Commands: ", style="bold")
        text.append("[Q]uit ", style="yellow")
        text.append("[R]efresh ", style="green")
        text.append("[E]xport Diagnostics ", style="blue")
        text.append("[H]ealth Check ", style="magenta")
        text.append("[C]lear Alerts", style="red")
        
        return Panel(text, style="dim")
        
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m {seconds%60:.0f}s"
        else:
            hours = seconds / 3600
            mins = (seconds % 3600) / 60
            return f"{hours:.0f}h {mins:.0f}m"
            
    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as time ago"""
        delta = datetime.now() - timestamp
        
        if delta.total_seconds() < 60:
            return f"{delta.total_seconds():.0f}s ago"
        elif delta.total_seconds() < 3600:
            return f"{delta.total_seconds()/60:.0f}m ago"
        else:
            return f"{delta.total_seconds()/3600:.1f}h ago"
            
    async def update_display(self, layout: Layout):
        """Update all dashboard panels"""
        layout["header"].update(self.generate_header())
        layout["status"].update(self.generate_status())
        layout["components"].update(self.generate_components())
        layout["metrics"].update(self.generate_metrics())
        layout["health"].update(self.generate_health())
        layout["alerts"].update(self.generate_alerts())
        layout["footer"].update(self.generate_footer())
        
    async def handle_input(self, key: str):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
        elif key.lower() == 'r':
            # Force refresh
            pass
        elif key.lower() == 'e':
            # Export diagnostics
            await self.orchestrator.export_diagnostics()
            logger.info("Diagnostics exported")
        elif key.lower() == 'h':
            # Run health check
            await self.orchestrator.run_health_check()
        elif key.lower() == 'c':
            # Clear alerts (would need to implement in health monitor)
            pass
            
    async def run(self):
        """Run the diagnostic dashboard"""
        self.running = True
        layout = self.create_layout()
        
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while self.running:
                try:
                    await self.update_display(layout)
                    await asyncio.sleep(self.refresh_interval)
                    
                except KeyboardInterrupt:
                    self.running = False
                except Exception as e:
                    logger.error(f"Dashboard error: {e}")
                    
                    
class SimpleDiagnostics:
    """Simple text-based diagnostics output"""
    
    def __init__(self, orchestrator: SystemOrchestrator):
        self.orchestrator = orchestrator
        
    def print_status(self):
        """Print current system status"""
        status = self.orchestrator.get_status()
        health = self.orchestrator.health.get_system_status()
        
        print("\n" + "="*60)
        print("SYSTEM STATUS REPORT")
        print("="*60)
        
        print(f"Status: {'RUNNING' if status['running'] else 'STOPPED'}")
        print(f"Health: {health.value.upper()}")
        print(f"Uptime: {timedelta(seconds=status['uptime'])}")
        print(f"Errors: {status['metrics']['errors']}")
        
        print("\nCOMPONENTS:")
        for name, created in status['components'].items():
            print(f"  - {name}: {'✓' if created else '✗'}")
            
        print("\nHEALTH METRICS:")
        system_health = self.orchestrator.health.get_component_health('system')
        if system_health:
            for name, metric in system_health.metrics.items():
                print(f"  - {name}: {metric.value}{metric.unit}")
                
        print("\nRECENT ALERTS:")
        alerts = self.orchestrator.health.get_recent_alerts(5)
        if alerts:
            for alert in alerts:
                print(f"  - [{alert.level.value}] {alert.component}: {alert.message}")
        else:
            print("  No recent alerts")
            
        print("="*60 + "\n")
        
    async def export_report(self, file_path: str = None):
        """Export full diagnostics report"""
        if not file_path:
            file_path = f"diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        diagnostics = self.orchestrator.get_diagnostics()
        
        with open(file_path, 'w') as f:
            json.dump(diagnostics, f, indent=2, default=str)
            
        print(f"Diagnostics report exported to: {file_path}")


# Usage example
async def run_dashboard(orchestrator: SystemOrchestrator):
    """Run the diagnostics dashboard"""
    dashboard = DiagnosticsDashboard(orchestrator)
    await dashboard.run()
    
    
def print_diagnostics(orchestrator: SystemOrchestrator):
    """Print simple diagnostics"""
    diag = SimpleDiagnostics(orchestrator)
    diag.print_status()