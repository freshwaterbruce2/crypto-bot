#!/usr/bin/env python3
"""
CRYPTO TRADING BOT PROJECT CLEANUP IMPLEMENTATION
Uses the new delete capability to perform the comprehensive cleanup identified

CLEANUP PHASES:
- Phase 1: Log files (198MB recovery)
- Phase 2: Duplicate files (15MB recovery)  
- Phase 3: Old scripts (10MB recovery)
- Phase 4: Documentation consolidation (5MB recovery)
"""

import sys
import os
from pathlib import Path

# Add current directory to path to import our delete capability
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from FILESYSTEM_DELETE_CAPABILITY import SafeFileDeleter
except ImportError:
    print("ERROR: FILESYSTEM_DELETE_CAPABILITY.py not found!")
    print("Please ensure the delete capability script is in the same directory.")
    sys.exit(1)

class CryptoTradingBotCleanup:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.deleter = SafeFileDeleter(project_root)
        
        # Define cleanup targets based on our analysis
        self.cleanup_targets = {
            "phase1_logs": [
                "kraken_infinity_bot.log",
                "bot_live_output.log", 
                "bot_output.log",
                "test_bot.log",
                "fixed_launch.log",
                "test_launch.log",
                "bot_test.log",
                "launch_output.log"
            ],
            
            "phase2_duplicates": {
                "websocket_versions": [
                    "src/exchange/websocket_manager_v2.py",
                    "src/exchange/websocket_manager_v2.py.backup.1752021429",
                    "src/exchange/websocket_manager_v2.py.backup.1752022763"
                ],
                "config_duplicates": [
                    "config.json.backup.1752022763",
                    "claude_desktop_config.json",
                    "claude_desktop_config_enhanced.json", 
                    "claude_desktop_config_fixed.json",
                    "claude_desktop_complete_config.json",
                    "claude_desktop_full_access_config.json",
                    "claude_desktop_organized_config.json"
                ],
                "balance_manager_old": [
                    "src/trading/unified_balance_manager.py",
                    "src/trading/real_time_balance_manager.py"
                ]
            },
            
            "phase3_old_scripts": [
                "fix_kraken_pro_websocket.py",
                "fix_websocket_nonce.py", 
                "websocket_v2_fix.py",
                "test_websocket_nonce_fix.py",
                "test_pro_websocket.py",
                "check_all_fixes.py",
                "test_comprehensive_balance_fix.py",
                "debug_balance_usdt.py",
                "final_fix_and_launch.py",
                "diagnose_balance_issue.py",
                "test_balance_fix.py",
                "debug_balance.py",
                "force_balance_refresh.py",
                "fix_and_test_simple.py",
                "fix_nonce_2025.py",
                "test_kraken_sdk_balance.py",
                "fix_confidence_format.py",
                "test_simplified_nonce.py",
                "test_balance_simple.py",
                "fix_nonce_sync.py"
            ],
            
            "phase4_documentation": [
                "COMPREHENSIVE_ANALYSIS_REPORT.md",
                "ENHANCED_MCP_SETUP_GUIDE.md", 
                "Kraken_websocket_V2_summarry.md",
                "IMPLEMENTATION_PLAN.md",
                "PROJECT_REVIEW_REPORT.md",
                "WEBSOCKET_FIX_INTEGRATION.md",
                "CLAUDE_CODE_RULES.md",
                "CLAUDE_CODE_SETUP_COMPLETE.md",
                "QUICK_FIXES.md",
                "CRITICAL_FIXES_APPLIED.md",
                "2025_OPTIMIZATION_STATUS_REPORT.md",
                "FINAL_STATUS_REPORT.md",
                "CLAUDE_CODE_TOOLS.md",
                "LAUNCH_GUIDE.md",
                "FINAL_FIX_SUMMARY.md",
                "POSITION_SIZE_FIX.md",
                "TRADING_BOT_FIXES_SUMMARY.md",
                "TRADING_FIX_SUMMARY.md",
                "RATE_LIMIT_FIX_SUMMARY.md",
                "BALANCE_FIX_COMPLETE.md",
                "LAUNCH_INSTRUCTIONS.md",
                "NONCE_FINAL_SOLUTION.md",
                "DIAGNOSTIC_SIGNAL_FLOW.md",
                "BOT_STATUS_SUCCESS.md",
                "BALANCE_DETECTION_ISSUE.md",
                "NONCE_ERROR_SOLUTION.md",
                "DECIMAL_FIX_SUMMARY.md",
                "FIX_BALANCE_MANAGER_CONFLICT.md",
                "CLAUDE_CODE_OPTIMIZATION.md",
                "CONFIDENCE_FORMAT_FIX.md",
                "SIGNAL_FORMAT_FIX_APPLIED.md",
                "INSTALLATION_CHECKLIST.md",
                "TEST_LAUNCH_SUMMARY.md",
                "SIGNAL_FORMAT_FIX.md",
                "WEBSOCKET_V2_INSTALLATION.md",
                "LEARNING_MANAGER_FIX.md"
            ]
        }
    
    def phase1_cleanup_logs(self) -> dict:
        """Phase 1: Clean up massive log files (198MB recovery)"""
        print("=== PHASE 1: LOG FILE CLEANUP ===")
        
        file_list = []
        for log_file in self.cleanup_targets["phase1_logs"]:
            file_path = self.project_root / log_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"Large log file cleanup - {log_file}"
                })
        
        results = self.deleter.stage_multiple_files(file_list, "phase1_logs")
        print(f"Phase 1 Results: {results['count']} files, {results['total_size_mb']:.2f} MB")
        return results
    
    def phase2_cleanup_duplicates(self) -> dict:
        """Phase 2: Remove duplicate files (15MB recovery)"""
        print("=== PHASE 2: DUPLICATE FILE CLEANUP ===")
        
        file_list = []
        
        # WebSocket duplicates
        for ws_file in self.cleanup_targets["phase2_duplicates"]["websocket_versions"]:
            file_path = self.project_root / ws_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"WebSocket duplicate - superseded by current version"
                })
        
        # Config duplicates  
        for config_file in self.cleanup_targets["phase2_duplicates"]["config_duplicates"]:
            file_path = self.project_root / config_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"Config duplicate - superseded by current config"
                })
        
        # Balance manager duplicates
        for balance_file in self.cleanup_targets["phase2_duplicates"]["balance_manager_old"]:
            file_path = self.project_root / balance_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"Balance manager duplicate - superseded by enhanced version"
                })
        
        results = self.deleter.stage_multiple_files(file_list, "phase2_duplicates")
        print(f"Phase 2 Results: {results['count']} files, {results['total_size_mb']:.2f} MB")
        return results
    
    def phase3_cleanup_scripts(self) -> dict:
        """Phase 3: Remove old fix/diagnostic scripts (10MB recovery)"""
        print("=== PHASE 3: OLD SCRIPT CLEANUP ===")
        
        file_list = []
        for script_file in self.cleanup_targets["phase3_old_scripts"]:
            file_path = self.project_root / script_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"Old diagnostic/fix script - fixes have been applied"
                })
        
        results = self.deleter.stage_multiple_files(file_list, "phase3_old_scripts")
        print(f"Phase 3 Results: {results['count']} files, {results['total_size_mb']:.2f} MB")
        return results
    
    def phase4_cleanup_documentation(self) -> dict:
        """Phase 4: Consolidate documentation (5MB recovery)"""
        print("=== PHASE 4: DOCUMENTATION CLEANUP ===")
        
        file_list = []
        for doc_file in self.cleanup_targets["phase4_documentation"]:
            file_path = self.project_root / doc_file
            if file_path.exists():
                file_list.append({
                    "path": str(file_path),
                    "reason": f"Redundant documentation - should be consolidated into README"
                })
        
        results = self.deleter.stage_multiple_files(file_list, "phase4_documentation")
        print(f"Phase 4 Results: {results['count']} files, {results['total_size_mb']:.2f} MB")
        return results
    
    def run_all_phases(self) -> dict:
        """Run all cleanup phases"""
        print("=== COMPREHENSIVE PROJECT CLEANUP ===")
        print(f"Project root: {self.project_root}")
        print(f"Staging directory: {self.deleter.staging_dir}")
        
        total_results = {
            "phase1": self.phase1_cleanup_logs(),
            "phase2": self.phase2_cleanup_duplicates(), 
            "phase3": self.phase3_cleanup_scripts(),
            "phase4": self.phase4_cleanup_documentation()
        }
        
        # Calculate totals
        total_files = sum(phase["count"] for phase in total_results.values())
        total_size_mb = sum(phase["total_size_mb"] for phase in total_results.values())
        
        print("\n=== CLEANUP SUMMARY ===")
        print(f"Total files staged: {total_files}")
        print(f"Total space recovered: {total_size_mb:.2f} MB")
        
        # Save log and generate recovery script
        log_file = self.deleter.save_log()
        recovery_script = self.deleter.generate_recovery_script()
        
        print(f"\nLog saved: {log_file}")
        print(f"Recovery script: {recovery_script}")
        
        # Show staging summary
        summary = self.deleter.get_staging_summary()
        print(f"\nStaging summary:")
        for category, info in summary["categories"].items():
            print(f"  {category}: {info['count']} files, {info['size_mb']:.2f} MB")
        
        return {
            "total_files": total_files,
            "total_size_mb": total_size_mb,
            "phases": total_results,
            "log_file": log_file,
            "recovery_script": recovery_script,
            "staging_summary": summary
        }
    
    def get_status(self) -> dict:
        """Get current staging status"""
        return self.deleter.get_staging_summary()
    
    def restore_all(self) -> dict:
        """Restore all staged files"""
        summary = self.deleter.get_staging_summary()
        restored = {"success": [], "failed": []}
        
        for item in summary["staged_items"]:
            if self.deleter.restore_file(item["original_path"]):
                restored["success"].append(item["original_path"])
            else:
                restored["failed"].append(item["original_path"])
        
        return restored
    
    def permanently_delete_all(self, confirm_delete: bool = False) -> dict:
        """Permanently delete all staged files - REQUIRES CONFIRMATION"""
        if not confirm_delete:
            print("ERROR: Permanent deletion requires confirm_delete=True")
            print("This will permanently delete all staged files!")
            return {"error": "Confirmation required"}
        
        return self.deleter.permanently_delete_staged(confirm=True)


def main():
    """Main execution function"""
    project_root = "C:\\projects050625\\projects\\active\\tool-crypto-trading-bot-2025"
    
    print("Crypto Trading Bot Project Cleanup")
    print("==================================")
    print(f"Project root: {project_root}")
    
    cleanup = CryptoTradingBotCleanup(project_root)
    
    return cleanup

if __name__ == "__main__":
    cleanup_system = main()
    print("\\nCleanup system ready!")
    print("Available commands:")
    print("- cleanup_system.run_all_phases()  # Stage all files for deletion")
    print("- cleanup_system.get_status()      # Check what's staged")
    print("- cleanup_system.restore_all()     # Restore all staged files")
    print("- cleanup_system.permanently_delete_all(confirm_delete=True)  # PERMANENT deletion")
