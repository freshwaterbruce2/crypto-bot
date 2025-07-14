#!/usr/bin/env python3
"""
FILESYSTEM DELETE CAPABILITY EXTENSION
Adds safe deletion functionality to the crypto trading bot project cleanup

FEATURES:
- Safe staging before deletion
- Comprehensive logging
- Recovery options
- Batch operations
- Size calculation and reporting
"""

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

class SafeFileDeleter:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.staging_dir = self.project_root / "_DELETION_STAGING"
        self.log_file = self.project_root / f"deletion_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.staged_items = []
        
        # Create staging directory
        self.staging_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(str(self.log_file).replace('.json', '.txt')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_file_info(self, file_path: Path) -> Dict:
        """Get comprehensive file information"""
        try:
            stat = file_path.stat()
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "hash": file_hash,
                "exists": True
            }
        except Exception as e:
            return {"path": str(file_path), "error": str(e), "exists": False}
    
    def stage_for_deletion(self, file_path: str, reason: str = "Cleanup", category: str = "general") -> bool:
        """Stage a file for deletion (move to staging area)"""
        source_path = Path(file_path)
        
        if not source_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return False
            
        # Get file info before moving
        file_info = self.get_file_info(source_path)
        
        # Create staged filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        staged_filename = f"{timestamp}_{source_path.name}"
        staged_path = self.staging_dir / category / staged_filename
        
        # Create category directory
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Move file to staging
            shutil.move(str(source_path), str(staged_path))
            
            # Record the operation
            staging_record = {
                "original_path": str(source_path),
                "staged_path": str(staged_path),
                "reason": reason,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "file_info": file_info,
                "status": "staged"
            }
            
            self.staged_items.append(staging_record)
            self.logger.info(f"STAGED: {source_path.name} ({file_info.get('size_mb', 0)} MB) - {reason}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stage {file_path}: {e}")
            return False
    
    def stage_multiple_files(self, file_list: List[Dict], category: str = "batch") -> Dict:
        """Stage multiple files for deletion"""
        results = {
            "staged": [],
            "failed": [],
            "total_size_mb": 0,
            "count": len(file_list)
        }
        
        for item in file_list:
            file_path = item.get("path", "")
            reason = item.get("reason", "Batch cleanup")
            
            if self.stage_for_deletion(file_path, reason, category):
                results["staged"].append(file_path)
                # Add size from file info if available
                for staged_item in self.staged_items:
                    if staged_item["original_path"] == file_path:
                        results["total_size_mb"] += staged_item["file_info"].get("size_mb", 0)
                        break
            else:
                results["failed"].append(file_path)
        
        return results
    
    def restore_file(self, original_path: str) -> bool:
        """Restore a staged file back to its original location"""
        for item in self.staged_items:
            if item["original_path"] == original_path and item["status"] == "staged":
                try:
                    staged_path = Path(item["staged_path"])
                    original_path_obj = Path(original_path)
                    
                    # Create original directory if needed
                    original_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move back
                    shutil.move(str(staged_path), str(original_path_obj))
                    
                    # Update status
                    item["status"] = "restored"
                    item["restored_timestamp"] = datetime.now().isoformat()
                    
                    self.logger.info(f"RESTORED: {original_path}")
                    return True
                    
                except Exception as e:
                    self.logger.error(f"Failed to restore {original_path}: {e}")
                    return False
        
        self.logger.warning(f"No staged file found for: {original_path}")
        return False
    
    def permanently_delete_staged(self, confirm: bool = False) -> Dict:
        """Permanently delete all staged files"""
        if not confirm:
            return {"error": "Must confirm permanent deletion with confirm=True"}
        
        results = {
            "deleted": [],
            "failed": [],
            "total_size_mb": 0,
            "count": 0
        }
        
        for item in self.staged_items:
            if item["status"] == "staged":
                try:
                    staged_path = Path(item["staged_path"])
                    if staged_path.exists():
                        staged_path.unlink()
                        item["status"] = "permanently_deleted"
                        item["deletion_timestamp"] = datetime.now().isoformat()
                        
                        results["deleted"].append(item["original_path"])
                        results["total_size_mb"] += item["file_info"].get("size_mb", 0)
                        results["count"] += 1
                        
                        self.logger.info(f"DELETED: {item['original_path']}")
                        
                except Exception as e:
                    results["failed"].append(item["original_path"])
                    self.logger.error(f"Failed to delete {item['original_path']}: {e}")
        
        return results
    
    def get_staging_summary(self) -> Dict:
        """Get summary of all staged items"""
        summary = {
            "total_staged": len([item for item in self.staged_items if item["status"] == "staged"]),
            "total_restored": len([item for item in self.staged_items if item["status"] == "restored"]),
            "total_deleted": len([item for item in self.staged_items if item["status"] == "permanently_deleted"]),
            "total_size_mb": sum(item["file_info"].get("size_mb", 0) for item in self.staged_items if item["status"] == "staged"),
            "categories": {},
            "staged_items": []
        }
        
        for item in self.staged_items:
            if item["status"] == "staged":
                category = item["category"]
                if category not in summary["categories"]:
                    summary["categories"][category] = {"count": 0, "size_mb": 0}
                
                summary["categories"][category]["count"] += 1
                summary["categories"][category]["size_mb"] += item["file_info"].get("size_mb", 0)
                
                summary["staged_items"].append({
                    "original_path": item["original_path"],
                    "reason": item["reason"],
                    "category": item["category"],
                    "size_mb": item["file_info"].get("size_mb", 0),
                    "timestamp": item["timestamp"]
                })
        
        return summary
    
    def save_log(self) -> str:
        """Save complete log to JSON file"""
        log_data = {
            "project_root": str(self.project_root),
            "log_created": datetime.now().isoformat(),
            "staged_items": self.staged_items,
            "summary": self.get_staging_summary()
        }
        
        with open(self.log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        self.logger.info(f"Log saved to: {self.log_file}")
        return str(self.log_file)
    
    def generate_recovery_script(self) -> str:
        """Generate PowerShell script to recover all staged files"""
        script_path = self.project_root / "EMERGENCY_RECOVERY.ps1"
        
        script_content = f"""# EMERGENCY RECOVERY SCRIPT
# Generated: {datetime.now().isoformat()}
# Restores all staged files back to original locations

$ProjectRoot = "{self.project_root}"
$StagingDir = "$ProjectRoot\\_DELETION_STAGING"

Write-Host "=== EMERGENCY RECOVERY STARTED ===" -ForegroundColor Red

"""
        
        for item in self.staged_items:
            if item["status"] == "staged":
                original = item["original_path"].replace("\\", "\\\\")
                staged = item["staged_path"].replace("\\", "\\\\") 
                
                script_content += f"""
# Restore: {item["reason"]}
if (Test-Path "{staged}") {{
    $OriginalDir = Split-Path "{original}" -Parent
    if (-not (Test-Path $OriginalDir)) {{
        New-Item -ItemType Directory -Path $OriginalDir -Force | Out-Null
    }}
    Move-Item "{staged}" "{original}" -Force
    Write-Host "RESTORED: {original}" -ForegroundColor Green
}} else {{
    Write-Host "NOT FOUND: {staged}" -ForegroundColor Yellow
}}
"""
        
        script_content += """
Write-Host "=== EMERGENCY RECOVERY COMPLETED ===" -ForegroundColor Red
"""
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return str(script_path)


def main():
    """Example usage of the SafeFileDeleter"""
    project_root = "C:\\projects050625\\projects\\active\\tool-crypto-trading-bot-2025"
    deleter = SafeFileDeleter(project_root)
    
    print("SafeFileDeleter initialized")
    print(f"Staging directory: {deleter.staging_dir}")
    print(f"Log file: {deleter.log_file}")
    
    return deleter

if __name__ == "__main__":
    deleter = main()
