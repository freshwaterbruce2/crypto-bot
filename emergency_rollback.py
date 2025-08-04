#!/usr/bin/env python3
"""
EMERGENCY ROLLBACK SCRIPT
========================
Restores files from backup: /mnt/c/dev/tools/crypto-trading-bot-2025/emergency_backups/nonce_fix_1754252007
Run this if the nonce fix causes issues.
"""

import shutil
from pathlib import Path

backup_dir = Path("/mnt/c/dev/tools/crypto-trading-bot-2025/emergency_backups/nonce_fix_1754252007")
project_root = Path("/mnt/c/dev/tools/crypto-trading-bot-2025")

print("🔄 Rolling back nonce fix...")
for backup_file in backup_dir.glob("*.py"):
    # Find original location - this is simplified, manual restore may be needed
    original_file = project_root / "src" / "utils" / backup_file.name
    if not original_file.exists():
        # Try other common locations
        for search_path in ["src/auth", "src/balance", "tests", "examples"]:
            potential_path = project_root / search_path / backup_file.name
            if potential_path.parent.exists():
                original_file = potential_path
                break
    
    if original_file.parent.exists():
        shutil.copy2(backup_file, original_file)
        print(f"✅ Restored: {backup_file.name}")

print("🔄 Rollback complete - check files manually")