#!/usr/bin/env python3
"""
Log Rotation Utility
Prevents disk space issues by rotating and compressing old logs
"""

import gzip
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LogRotationManager:
    """Manages log rotation to prevent disk space issues"""

    def __init__(self,
                 log_dir: str = "logs",
                 max_log_size_mb: int = 50,
                 keep_days: int = 7,
                 compress_after_days: int = 1,
                 disk_space_threshold_pct: int = 90):
        """
        Initialize log rotation manager

        Args:
            log_dir: Directory containing logs
            max_log_size_mb: Maximum size of a log file before rotation
            keep_days: Number of days to keep logs
            compress_after_days: Compress logs older than this many days
            disk_space_threshold_pct: Disk usage percentage to trigger cleanup
        """
        self.log_dir = Path(log_dir)
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        self.keep_days = keep_days
        self.compress_after_days = compress_after_days
        self.disk_space_threshold_pct = disk_space_threshold_pct

    def check_disk_space(self) -> float:
        """Check current disk usage percentage"""
        try:
            import psutil
            # Check the actual drive where logs are stored
            disk_path = str(self.log_dir.resolve())
            # On Windows, get the drive letter
            if os.name == 'nt' and len(disk_path) > 1 and disk_path[1] == ':':
                disk_path = disk_path[:3]  # e.g., "C:\"
            else:
                disk_path = '/'

            disk_usage = psutil.disk_usage(disk_path)
            return disk_usage.percent
        except ImportError:
            # Fallback to os.statvfs for Unix systems
            statvfs = os.statvfs(str(self.log_dir))
            total = statvfs.f_frsize * statvfs.f_blocks
            free = statvfs.f_frsize * statvfs.f_avail
            used_percent = ((total - free) / total) * 100
            return used_percent

    def rotate_large_files(self) -> list[str]:
        """Rotate files that exceed size limit"""
        rotated_files = []

        if not self.log_dir.exists():
            return rotated_files

        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_size > self.max_log_size_bytes:
                # Create rotated filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{log_file.stem}_{timestamp}.log"
                rotated_path = log_file.parent / rotated_name

                try:
                    # Move the file
                    shutil.move(str(log_file), str(rotated_path))

                    # Create new empty log file
                    log_file.touch()

                    rotated_files.append(str(rotated_path))
                    logger.info(f"Rotated large log file: {log_file.name} -> {rotated_name}")
                except Exception as e:
                    logger.error(f"Failed to rotate {log_file}: {e}")

        return rotated_files

    def compress_old_logs(self) -> int:
        """Compress logs older than compress_after_days"""
        compressed_count = 0
        cutoff_time = time.time() - (self.compress_after_days * 86400)

        if not self.log_dir.exists():
            return compressed_count

        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                gz_file = log_file.with_suffix('.log.gz')

                try:
                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(gz_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # Remove original file
                    log_file.unlink()
                    compressed_count += 1
                    logger.info(f"Compressed old log: {log_file.name}")
                except Exception as e:
                    logger.error(f"Failed to compress {log_file}: {e}")

        return compressed_count

    def delete_old_logs(self) -> int:
        """Delete logs older than keep_days"""
        deleted_count = 0
        cutoff_time = time.time() - (self.keep_days * 86400)

        if not self.log_dir.exists():
            return deleted_count

        # Delete old uncompressed logs
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    # On Windows, try to truncate if deletion fails
                    if os.name == 'nt':
                        try:
                            log_file.unlink()
                            deleted_count += 1
                            logger.info(f"Deleted old log: {log_file.name}")
                        except PermissionError:
                            with open(log_file, 'w') as f:
                                f.truncate(0)
                            deleted_count += 1
                            logger.info(f"Truncated old log: {log_file.name}")
                    else:
                        log_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old log: {log_file.name}")
                except Exception as e:
                    logger.debug(f"Could not clean {log_file}: {e}")

        # Delete old compressed logs
        for gz_file in self.log_dir.glob("*.log.gz"):
            if gz_file.stat().st_mtime < cutoff_time:
                try:
                    gz_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old compressed log: {gz_file.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {gz_file}: {e}")

        return deleted_count

    def emergency_cleanup(self) -> int:
        """Emergency cleanup when disk space is critical"""
        logger.warning("Performing emergency log cleanup due to disk space!")
        deleted_count = 0

        if not self.log_dir.exists():
            return deleted_count

        # Delete oldest logs first
        log_files = []
        for pattern in ["*.log", "*.log.gz"]:
            log_files.extend(list(self.log_dir.glob(pattern)))

        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: x.stat().st_mtime)

        # Delete oldest 50% of files
        files_to_delete = len(log_files) // 2
        for log_file in log_files[:files_to_delete]:
            try:
                # On Windows, try to truncate the file instead of deleting if it's locked
                if os.name == 'nt':
                    try:
                        # Try to delete first
                        log_file.unlink()
                        deleted_count += 1
                        logger.info(f"Emergency deleted: {log_file.name}")
                    except PermissionError:
                        # If deletion fails, truncate the file to 0 bytes
                        with open(log_file, 'w') as f:
                            f.truncate(0)
                        deleted_count += 1
                        logger.info(f"Emergency truncated: {log_file.name}")
                else:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"Emergency deleted: {log_file.name}")
            except Exception as e:
                logger.debug(f"Could not clean {log_file}: {e}")

        return deleted_count

    def run_rotation(self) -> dict:
        """Run complete log rotation process"""
        results = {
            'disk_usage_before': self.check_disk_space(),
            'rotated_files': [],
            'compressed_count': 0,
            'deleted_count': 0,
            'emergency_cleanup': False
        }

        logger.info(f"Starting log rotation. Disk usage: {results['disk_usage_before']:.1f}%")

        # Check if emergency cleanup is needed
        if results['disk_usage_before'] > self.disk_space_threshold_pct:
            results['emergency_cleanup'] = True
            results['deleted_count'] += self.emergency_cleanup()

        # Normal rotation process
        results['rotated_files'] = self.rotate_large_files()
        results['compressed_count'] = self.compress_old_logs()
        results['deleted_count'] += self.delete_old_logs()

        # Check disk usage after cleanup
        results['disk_usage_after'] = self.check_disk_space()

        logger.info(
            f"Log rotation complete. "
            f"Rotated: {len(results['rotated_files'])}, "
            f"Compressed: {results['compressed_count']}, "
            f"Deleted: {results['deleted_count']}, "
            f"Disk usage: {results['disk_usage_before']:.1f}% -> {results['disk_usage_after']:.1f}%"
        )

        return results


def setup_automatic_rotation(config: dict) -> Optional[LogRotationManager]:
    """Set up automatic log rotation based on config"""
    try:
        # Get log configuration
        log_dir = config.get('log_dir', 'logs')
        max_size_mb = config.get('log_max_size_mb', 50)
        keep_days = config.get('log_rotation_days', 7)

        # Create rotation manager
        rotation_manager = LogRotationManager(
            log_dir=log_dir,
            max_log_size_mb=max_size_mb,
            keep_days=keep_days
        )

        # Run initial rotation
        rotation_manager.run_rotation()

        return rotation_manager

    except Exception as e:
        logger.error(f"Failed to set up log rotation: {e}")
        return None


# Standalone script execution
if __name__ == "__main__":
    import sys

    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Default log directory
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs"

    # Create and run rotation
    manager = LogRotationManager(log_dir=log_dir)
    results = manager.run_rotation()

    print("\nLog Rotation Results:")
    print(f"- Disk usage: {results['disk_usage_before']:.1f}% -> {results['disk_usage_after']:.1f}%")
    print(f"- Files rotated: {len(results['rotated_files'])}")
    print(f"- Files compressed: {results['compressed_count']}")
    print(f"- Files deleted: {results['deleted_count']}")
    print(f"- Emergency cleanup: {results['emergency_cleanup']}")
