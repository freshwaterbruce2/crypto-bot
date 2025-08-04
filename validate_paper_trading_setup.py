#!/usr/bin/env python3
"""
Paper Trading Setup Validator
Comprehensive validation script to ensure paper trading environment is properly configured
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class PaperTradingValidator:
    """Comprehensive validator for paper trading setup"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.validation_results = {}
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()
        
    def setup_logging(self):
        """Setup logging for validation"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.project_root / "paper_trading_validation.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def validate_environment_file(self) -> Tuple[bool, List[str]]:
        """Validate .env.paper_trading file exists and has correct settings"""
        env_file = self.project_root / ".env.paper_trading"
        errors = []
        
        if not env_file.exists():
            errors.append(f"Environment file not found: {env_file}")
            return False, errors
        
        # Load and validate environment variables
        required_vars = {
            'PAPER_TRADING_ENABLED': 'true',
            'LIVE_TRADING_DISABLED': 'true',
            'TRADING_MODE': 'paper',
            'FORCE_PAPER_MODE': 'true',
            'DISABLE_REAL_ORDERS': 'true',
            'SAFETY_MODE': 'maximum'
        }
        
        env_vars = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        for var, expected_value in required_vars.items():
            if var not in env_vars:
                errors.append(f"Required environment variable missing: {var}")
            elif env_vars[var] != expected_value:
                errors.append(f"Incorrect value for {var}: got '{env_vars[var]}', expected '{expected_value}'")
        
        # Validate numeric limits
        numeric_vars = {
            'PAPER_STARTING_BALANCE': (100.0, 200.0),
            'MAX_POSITION_SIZE_USD': (5.0, 15.0),
            'MAX_DAILY_TRADES': (10, 100),
            'CIRCUIT_BREAKER_LOSS_USD': (15.0, 50.0)
        }
        
        for var, (min_val, max_val) in numeric_vars.items():
            if var in env_vars:
                try:
                    value = float(env_vars[var])
                    if not (min_val <= value <= max_val):
                        self.warnings.append(f"{var} value {value} outside recommended range [{min_val}, {max_val}]")
                except ValueError:
                    errors.append(f"Invalid numeric value for {var}: {env_vars[var]}")
        
        return len(errors) == 0, errors
    
    def validate_configuration_file(self) -> Tuple[bool, List[str]]:
        """Validate paper_trading_config.json"""
        config_file = self.project_root / "paper_trading_config.json"
        errors = []
        
        if not config_file.exists():
            errors.append(f"Configuration file not found: {config_file}")
            return False, errors
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate structure
            required_sections = [
                'paper_trading',
                'virtual_account',
                'trading_limits',
                'risk_management',
                'safety_protocols',
                'monitoring'
            ]
            
            for section in required_sections:
                if section not in config:
                    errors.append(f"Missing configuration section: {section}")
            
            # Validate paper trading is enabled
            if not config.get('paper_trading', {}).get('enabled', False):
                errors.append("Paper trading not enabled in configuration")
            
            # Validate safety protocols
            safety = config.get('safety_protocols', {})
            if not safety.get('multi_layer_protection', False):
                errors.append("Multi-layer protection not enabled")
            
            if not safety.get('api_call_blocking', {}).get('block_real_orders', False):
                errors.append("Real order blocking not enabled")
            
            # Validate virtual account
            virtual_account = config.get('virtual_account', {})
            starting_balance = virtual_account.get('starting_balance', 0)
            if starting_balance < 100 or starting_balance > 200:
                self.warnings.append(f"Starting balance ${starting_balance} outside recommended range [$100-$200]")
            
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            errors.append(f"Error reading configuration file: {e}")
        
        return len(errors) == 0, errors
    
    def validate_directory_structure(self) -> Tuple[bool, List[str]]:
        """Validate required directories exist or can be created"""
        errors = []
        
        required_dirs = [
            self.project_root / "paper_trading_data",
            self.project_root / "paper_trading_data" / "logs",
            self.project_root / "paper_trading_data" / "reports",
            self.project_root / "paper_trading_data" / "backups",
            Path("D:/trading_data/logs/paper_trading")
        ]
        
        for dir_path in required_dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                if not dir_path.exists():
                    errors.append(f"Cannot create directory: {dir_path}")
            except Exception as e:
                errors.append(f"Error creating directory {dir_path}: {e}")
        
        return len(errors) == 0, errors
    
    def validate_paper_trading_modules(self) -> Tuple[bool, List[str]]:
        """Validate paper trading Python modules can be imported"""
        errors = []
        
        modules_to_test = [
            'src.paper_trading.paper_config',
            'src.paper_trading.paper_exchange',
            'src.paper_trading.paper_executor',
            'src.paper_trading.paper_performance_tracker',
            'src.utils.professional_logging_system'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                errors.append(f"Cannot import {module_name}: {e}")
            except Exception as e:
                errors.append(f"Error importing {module_name}: {e}")
        
        return len(errors) == 0, errors
    
    def validate_launcher_script(self) -> Tuple[bool, List[str]]:
        """Validate the paper trading launcher exists and is executable"""
        errors = []
        
        launcher_script = self.project_root / "launch_paper_trading.py"
        if not launcher_script.exists():
            errors.append(f"Launcher script not found: {launcher_script}")
        else:
            # Check if script is executable
            if not os.access(launcher_script, os.X_OK):
                self.warnings.append(f"Launcher script not executable: {launcher_script}")
        
        return len(errors) == 0, errors
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """Validate required Python dependencies are installed"""
        errors = []
        
        required_packages = [
            'asyncio',
            'json',
            'pathlib',
            'logging',
            'datetime'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                errors.append(f"Required package not available: {package}")
        
        return len(errors) == 0, errors
    
    def create_validation_report(self):
        """Create comprehensive validation report"""
        report = {
            "validation_timestamp": self.start_time.isoformat(),
            "validation_duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "overall_status": "PASSED" if len(self.errors) == 0 else "FAILED",
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "validation_results": self.validation_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "recommendations": []
        }
        
        # Add recommendations based on results
        if len(self.errors) > 0:
            report["recommendations"].append("Fix all errors before attempting to launch paper trading")
        
        if len(self.warnings) > 0:
            report["recommendations"].append("Review warnings and adjust configuration as needed")
        
        if len(self.errors) == 0:
            report["recommendations"].extend([
                "Configuration validation passed - ready for paper trading",
                "Use 'python launch_paper_trading.py' to start paper trading",
                "Monitor logs in D:/trading_data/logs/paper_trading/",
                "Check status with 'python check_paper_trading_status.py'"
            ])
        
        # Save report
        report_file = self.project_root / "paper_trading_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def run_validation(self):
        """Run complete validation suite"""
        print("🧪 PAPER TRADING SETUP VALIDATION")
        print("=" * 50)
        print(f"Validation started: {self.start_time}")
        print()
        
        validation_tests = [
            ("Environment File", self.validate_environment_file),
            ("Configuration File", self.validate_configuration_file),
            ("Directory Structure", self.validate_directory_structure),
            ("Python Modules", self.validate_paper_trading_modules),
            ("Launcher Script", self.validate_launcher_script),
            ("Dependencies", self.validate_dependencies)
        ]
        
        for test_name, test_function in validation_tests:
            print(f"Testing {test_name}...", end=" ")
            try:
                passed, test_errors = test_function()
                if passed:
                    print("✓ PASSED")
                else:
                    print("✗ FAILED")
                    self.errors.extend(test_errors)
                
                self.validation_results[test_name] = {
                    "passed": passed,
                    "errors": test_errors
                }
            except Exception as e:
                print(f"✗ ERROR: {e}")
                self.errors.append(f"{test_name}: {str(e)}")
                self.validation_results[test_name] = {
                    "passed": False,
                    "errors": [str(e)]
                }
        
        # Create and display report
        report = self.create_validation_report()
        
        print()
        print("=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Total Errors: {report['total_errors']}")
        print(f"Total Warnings: {report['total_warnings']}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if report['recommendations']:
            print("\n📝 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        print(f"\nValidation report saved: paper_trading_validation_report.json")
        print("=" * 50)
        
        return report['overall_status'] == 'PASSED'

def main():
    """Main entry point"""
    validator = PaperTradingValidator()
    validator.setup_logging()
    
    success = validator.run_validation()
    
    if success:
        print("\n✅ VALIDATION PASSED - Ready for paper trading!")
        print("Next step: python launch_paper_trading.py")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION FAILED - Please fix errors before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()