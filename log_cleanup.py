#!/usr/bin/env python3
"""
Log Cleanup Script - Prevent massive log files
Automatically truncates and rotates large log files
"""

import os
import logging
from datetime import datetime
from pathlib import Path

def cleanup_logs():
    """Clean up large log files to prevent disk space issues"""
    
    log_file = Path("kraken_infinity_bot.log")
    max_size_mb = 50  # Maximum log file size in MB
    keep_lines = 10000  # Number of recent lines to keep
    
    if not log_file.exists():
        print("No log file found to clean")
        return
    
    # Check file size
    size_mb = log_file.stat().st_size / (1024 * 1024)
    print(f"Current log file size: {size_mb:.1f} MB")
    
    if size_mb > max_size_mb:
        print(f"Log file exceeds {max_size_mb}MB, cleaning up...")
        
        # Create backup with timestamp
        backup_name = f"kraken_infinity_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        backup_path = Path(backup_name)
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if len(lines) > keep_lines:
            # Keep only recent lines
            recent_lines = lines[-keep_lines:]
            
            # Write recent lines back to main log
            with open(log_file, 'w', encoding='utf-8') as f:
                f.writelines(recent_lines)
            
            print(f"Truncated log to {keep_lines} most recent lines")
            print(f"Reduced size: {log_file.stat().st_size / (1024 * 1024):.1f} MB")
        
        # Clean up old backups (keep only 3 most recent)
        backup_files = sorted(Path('.').glob('kraken_infinity_bot_backup_*.log'))
        if len(backup_files) > 3:
            for old_backup in backup_files[:-3]:
                try:
                    old_backup.unlink()
                    print(f"Removed old backup: {old_backup}")
                except:
                    pass
    
    else:
        print("Log file size is acceptable")

if __name__ == "__main__":
    cleanup_logs()