"""
Example: Running the Trading Bot with Full Orchestration

This example shows how to use the system orchestrator for complete
system management and monitoring.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.orchestrator import (
    SystemOrchestrator,
    ConfigManager,
    HealthMonitor,
    StartupSequence,
    DiagnosticsDashboard,
    SimpleDiagnostics
)
from src.orchestrator.bot_integration import OrchestratedTradingBot


async def basic_example():
    """Basic orchestrated bot example"""
    print("=== Basic Orchestrated Bot Example ===\n")
    
    # Create orchestrator
    orchestrator = SystemOrchestrator('config.json')
    
    # Initialize system
    print("Initializing system...")
    success = await orchestrator.initialize()
    
    if not success:
        print("System initialization failed!")
        return
        
    print("System initialized successfully!")
    
    # Get status
    status = orchestrator.get_status()
    print(f"System health: {orchestrator.health.get_system_status().value}")
    print(f"Components loaded: {sum(1 for c in status['components'].values() if c)}")
    
    # Run for a bit
    print("\nSystem running... (press Ctrl+C to stop)")
    try:
        await asyncio.sleep(10)
    except KeyboardInterrupt:
        pass
        
    # Shutdown
    print("\nShutting down...")
    await orchestrator.shutdown()
    print("Shutdown complete!")


async def full_trading_example():
    """Full trading bot with orchestration"""
    print("=== Full Orchestrated Trading Bot Example ===\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrated bot
    bot = OrchestratedTradingBot('config.json')
    
    try:
        # Initialize
        print("Initializing trading bot with full orchestration...")
        await bot.initialize()
        
        # Print status
        status = bot.get_status()
        print(f"\nOrchestrator Status: {status['orchestrator']['health']}")
        print(f"Components: {status['orchestrator']['components']}")
        
        # Update configuration example
        print("\nUpdating configuration...")
        await bot.update_config('trading.profit_target', 0.007)
        print("Configuration updated!")
        
        # Start trading
        print("\nStarting trading bot...")
        await bot.start()
        
        # Run for demonstration
        print("Bot is running... (will stop in 30 seconds)")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Export diagnostics on error
        print("Exporting diagnostics...")
        await bot.orchestrator.export_diagnostics()
        
    finally:
        # Stop bot
        print("\nStopping bot...")
        await bot.stop()
        print("Bot stopped!")


async def monitoring_example():
    """System monitoring example"""
    print("=== System Monitoring Example ===\n")
    
    # Create orchestrator
    orchestrator = SystemOrchestrator('config.json')
    
    # Initialize
    await orchestrator.initialize()
    
    # Simple diagnostics
    print("Current System Status:")
    diag = SimpleDiagnostics(orchestrator)
    diag.print_status()
    
    # Monitor for a while
    print("\nMonitoring system for 20 seconds...")
    
    for i in range(4):
        await asyncio.sleep(5)
        
        # Run health check
        health = await orchestrator.run_health_check()
        
        print(f"\nHealth Check #{i+1}:")
        for component, status in health.items():
            print(f"  {component}: {status.status.value}")
            
    # Export report
    print("\nExporting diagnostics report...")
    await diag.export_report()
    
    # Shutdown
    await orchestrator.shutdown()


async def dashboard_example():
    """Interactive dashboard example"""
    print("=== Interactive Dashboard Example ===\n")
    
    # Create orchestrator
    orchestrator = SystemOrchestrator('config.json')
    
    # Initialize
    print("Initializing system...")
    await orchestrator.initialize()
    
    print("Launching dashboard...")
    print("(Press Q to quit, R to refresh, E to export diagnostics)\n")
    
    # Run dashboard
    dashboard = DiagnosticsDashboard(orchestrator)
    
    try:
        await dashboard.run()
    finally:
        await orchestrator.shutdown()


async def configuration_example():
    """Configuration management example"""
    print("=== Configuration Management Example ===\n")
    
    # Create config manager directly
    config = ConfigManager('./config')
    await config.initialize()
    
    # Get configuration values
    print("Current Configuration:")
    print(f"  Exchange: {config.get('exchange.name')}")
    print(f"  Trading pairs: {len(config.get('trading.pairs', []))}")
    print(f"  Profit target: {config.get('trading.profit_target')}")
    print(f"  Rate limit tier: {config.get('rate_limiting.tier')}")
    
    # Update configuration
    print("\nUpdating configuration...")
    config.set('trading.profit_target', 0.008)
    config.set('monitoring.metrics_interval', 5)
    
    # Save configuration
    await config.save_config()
    print("Configuration saved!")
    
    # Subscribe to changes
    def on_config_change(cfg):
        print(f"Configuration changed!")
        
    config.subscribe(on_config_change)
    
    # Test hot reload
    print("\nTesting configuration hot reload...")
    await config.reload_config()
    
    await config.shutdown()


async def health_monitoring_example():
    """Health monitoring with recovery example"""
    print("=== Health Monitoring Example ===\n")
    
    orchestrator = SystemOrchestrator('config.json')
    await orchestrator.initialize()
    
    # Register custom health check
    class CustomHealthCheck:
        def __init__(self):
            self.name = "custom_service"
            self.fail_count = 0
            
        async def check(self):
            from src.orchestrator.health_monitor import ComponentHealth, HealthStatus, HealthMetric
            
            health = ComponentHealth(
                name=self.name,
                status=HealthStatus.HEALTHY if self.fail_count < 3 else HealthStatus.CRITICAL
            )
            
            # Simulate degradation
            self.fail_count += 1
            
            health.add_metric(HealthMetric(
                name="error_rate",
                value=self.fail_count * 0.1,
                unit="%",
                threshold_warning=0.2,
                threshold_critical=0.3
            ))
            
            return health
            
    # Register the health check
    custom_check = CustomHealthCheck()
    orchestrator.health.register_health_check(custom_check)
    
    # Register recovery handler
    async def recover_custom_service():
        print("Attempting to recover custom service...")
        custom_check.fail_count = 0
        print("Custom service recovered!")
        
    orchestrator.health.register_recovery_handler('custom_service', recover_custom_service)
    
    # Monitor health
    print("Monitoring health (will degrade and recover)...")
    
    for i in range(8):
        await asyncio.sleep(2)
        
        health = orchestrator.health.get_component_health('custom_service')
        if health:
            print(f"Check #{i+1}: {health.status.value} "
                  f"(error_rate: {health.metrics['error_rate'].value:.1f}%)")
            
    await orchestrator.shutdown()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Orchestrated Trading Bot Examples')
    parser.add_argument(
        'example',
        choices=['basic', 'trading', 'monitoring', 'dashboard', 'config', 'health'],
        help='Example to run'
    )
    
    args = parser.parse_args()
    
    examples = {
        'basic': basic_example,
        'trading': full_trading_example,
        'monitoring': monitoring_example,
        'dashboard': dashboard_example,
        'config': configuration_example,
        'health': health_monitoring_example
    }
    
    asyncio.run(examples[args.example]())


if __name__ == "__main__":
    main()