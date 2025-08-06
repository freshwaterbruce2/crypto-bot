#!/usr/bin/env python3
"""
Clean up unused and obsolete files from the crypto trading bot project
"""

import os
import shutil
from pathlib import Path
import json

# Project root
PROJECT_ROOT = Path(__file__).parent

# Files and patterns to remove
REMOVE_PATTERNS = [
    # Old test files (no longer needed)
    "test_*.py",
    "validate_*.py",
    "diagnose_*.py",
    "fix_nonce_*.py",
    "fix_balance_*.py",
    "fix_websocket_*.py",
    "emergency_diagnostics_*.json",
    "emergency_rollback.py",
    
    # Old validation reports
    "*_validation_report*.json",
    "*_integration_test_report*.json",
    "*_compliance_report*.json",
    "*_status_report*.json",
    
    # Backup files
    "*.backup",
    "*_backup*",
    "nonce_state*.json",
    "nonce_state*.backup",
    
    # Old batch files (Windows)
    "TEST_*.bat",
    "FIX_*.bat",
    "DIAGNOSE_*.bat",
    "CHECK_*.bat",
    "VALIDATE_*.bat",
    
    # Temporary fix files
    "apply_websocket_v2_fix.py",
    "patch_rest_client.py",
    "fix_all_nonce_issues.py",
    "fix_dependencies.bat",
    "memory_optimization_fixes.py",
    "performance_optimizations.py",
    "database_optimization_fixes.py",
    "rate_limiting_optimization_fixes.py",
    "websocket_optimization_fixes.py",
    
    # Old launchers (replaced by simple_launcher.py)
    "launch_bot_fixed.py",
    "launch_fixed_bot.py",
    "clean_startup.py",
    "simple_startup_test.py",
    
    # Version files (not needed)
    "0.*.0",
    "=*.*.* ",
    
    # Old documentation (will keep main docs)
    "*_FIX_COMPLETE.md",
    "*_FIX_SUMMARY.md",
    "*_FIXES_SUMMARY.md",
]

# Directories to remove
REMOVE_DIRS = [
    "emergency_backups",
    "websocket_v2_backup",
    "__pycache__",
    ".pytest_cache",
]

# Files to keep (whitelist)
KEEP_FILES = [
    "simple_launcher.py",
    "main.py",
    "config.json",
    "requirements.txt",
    "README.md",
    ".env",
    ".env.template",
    "CLAUDE.md",
]

def should_remove_file(file_path: Path) -> bool:
    """Check if a file should be removed"""
    # Keep whitelisted files
    if file_path.name in KEEP_FILES:
        return False
    
    # Check removal patterns
    for pattern in REMOVE_PATTERNS:
        if file_path.match(pattern):
            return True
    
    return False

def clean_project():
    """Clean up the project"""
    removed_files = []
    removed_dirs = []
    
    print("🧹 Starting cleanup of unused files...")
    
    # Remove individual files
    for file_path in PROJECT_ROOT.rglob("*"):
        if file_path.is_file() and should_remove_file(file_path):
            try:
                print(f"  Removing: {file_path.relative_to(PROJECT_ROOT)}")
                file_path.unlink()
                removed_files.append(str(file_path.relative_to(PROJECT_ROOT)))
            except Exception as e:
                print(f"  ⚠️  Could not remove {file_path.name}: {e}")
    
    # Remove directories
    for dir_name in REMOVE_DIRS:
        for dir_path in PROJECT_ROOT.rglob(dir_name):
            if dir_path.is_dir():
                try:
                    print(f"  Removing directory: {dir_path.relative_to(PROJECT_ROOT)}")
                    shutil.rmtree(dir_path)
                    removed_dirs.append(str(dir_path.relative_to(PROJECT_ROOT)))
                except Exception as e:
                    print(f"  ⚠️  Could not remove directory {dir_path.name}: {e}")
    
    # Clean up empty directories
    for dir_path in sorted(PROJECT_ROOT.rglob("*"), reverse=True):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                print(f"  Removed empty directory: {dir_path.relative_to(PROJECT_ROOT)}")
            except:
                pass
    
    # Summary
    print(f"\n✅ Cleanup complete!")
    print(f"  - Removed {len(removed_files)} files")
    print(f"  - Removed {len(removed_dirs)} directories")
    
    # Save cleanup log
    cleanup_log = {
        "timestamp": str(Path(__file__).stat().st_mtime),
        "removed_files": removed_files,
        "removed_directories": removed_dirs,
        "total_files": len(removed_files),
        "total_directories": len(removed_dirs)
    }
    
    log_file = PROJECT_ROOT / "cleanup_log.json"
    with open(log_file, 'w') as f:
        json.dump(cleanup_log, f, indent=2)
    
    print(f"\n📝 Cleanup log saved to: {log_file}")
    
    return cleanup_log

if __name__ == "__main__":
    # Confirm before cleaning
    print("⚠️  This will remove old test files, validation scripts, and backups.")
    print("   Essential files (main.py, config.json, etc.) will be preserved.")
    response = input("\nProceed with cleanup? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        clean_project()
    else:
        print("Cleanup cancelled.")