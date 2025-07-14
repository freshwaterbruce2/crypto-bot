#!/usr/bin/env python3
"""
Python Cache Cleanup Script
============================

Removes all Python bytecode cache files that can cause compatibility issues
between different Python versions (especially Python 3.13 cache files).

This script should be run whenever:
- Switching Python versions
- Encountering import errors
- Before deploying to production
- After major code changes
"""

import os
import shutil
import sys
from pathlib import Path

def cleanup_python_cache(root_path: Path):
    """Clean up all Python cache files and directories"""
    
    print("🧹 Python Cache Cleanup Tool")
    print("=" * 40)
    print(f"Cleaning cache files in: {root_path}")
    
    # Counters
    pycache_dirs_removed = 0
    pyc_files_removed = 0
    pyo_files_removed = 0
    
    # Remove __pycache__ directories
    print("\n1. Removing __pycache__ directories...")
    for pycache_dir in root_path.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
            pycache_dirs_removed += 1
            print(f"   ✓ Removed: {pycache_dir.relative_to(root_path)}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pycache_dir}: {e}")
    
    # Remove .pyc files
    print("\n2. Removing .pyc files...")
    for pyc_file in root_path.rglob("*.pyc"):
        try:
            pyc_file.unlink()
            pyc_files_removed += 1
            print(f"   ✓ Removed: {pyc_file.relative_to(root_path)}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pyc_file}: {e}")
    
    # Remove .pyo files
    print("\n3. Removing .pyo files...")
    for pyo_file in root_path.rglob("*.pyo"):
        try:
            pyo_file.unlink()
            pyo_files_removed += 1
            print(f"   ✓ Removed: {pyo_file.relative_to(root_path)}")
        except Exception as e:
            print(f"   ❌ Failed to remove {pyo_file}: {e}")
    
    # Additional cleanup for problematic locations
    print("\n4. Cleaning problematic cache locations...")
    problematic_paths = [
        root_path / "src" / "core" / "__pycache__",
        root_path / "src" / "utils" / "__pycache__", 
        root_path / "src" / "learning" / "__pycache__",
        root_path / "src" / "assistants" / "__pycache__",
        root_path / "src" / "trading" / "__pycache__",
        root_path / "extensions" / "**" / "__pycache__"
    ]
    
    for pattern_path in problematic_paths:
        if "*" in str(pattern_path):
            # Handle glob patterns
            for path in root_path.glob(str(pattern_path.relative_to(root_path))):
                if path.is_dir():
                    try:
                        shutil.rmtree(path)
                        print(f"   ✓ Removed problematic cache: {path.relative_to(root_path)}")
                    except Exception as e:
                        print(f"   ❌ Failed to remove {path}: {e}")
        else:
            if pattern_path.exists():
                try:
                    shutil.rmtree(pattern_path)
                    print(f"   ✓ Removed problematic cache: {pattern_path.relative_to(root_path)}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {pattern_path}: {e}")
    
    # Summary
    print("\n" + "=" * 40)
    print("🎉 Cleanup Complete!")
    print(f"   📁 __pycache__ directories removed: {pycache_dirs_removed}")
    print(f"   📄 .pyc files removed: {pyc_files_removed}")
    print(f"   📄 .pyo files removed: {pyo_files_removed}")
    print(f"   📊 Total items cleaned: {pycache_dirs_removed + pyc_files_removed + pyo_files_removed}")
    
    # Verification
    print("\n5. Verification...")
    remaining_cache = list(root_path.rglob("__pycache__")) + list(root_path.rglob("*.pyc")) + list(root_path.rglob("*.pyo"))
    if remaining_cache:
        print(f"   ⚠️  Warning: {len(remaining_cache)} cache items still remain")
        for item in remaining_cache[:5]:  # Show first 5
            print(f"      - {item.relative_to(root_path)}")
        if len(remaining_cache) > 5:
            print(f"      ... and {len(remaining_cache) - 5} more")
    else:
        print("   ✅ All cache files successfully removed!")
    
    return pycache_dirs_removed + pyc_files_removed + pyo_files_removed

def main():
    """Main entry point"""
    
    # Get project root
    project_root = Path(__file__).parent
    
    print(f"Python version: {sys.version}")
    print(f"Project root: {project_root}")
    
    # Run cleanup
    total_cleaned = cleanup_python_cache(project_root)
    
    if total_cleaned > 0:
        print(f"\n✅ Cache cleanup successful! ({total_cleaned} items removed)")
        print("💡 Tip: Run this script whenever you encounter import errors")
        print("💡 Tip: This is especially important when switching Python versions")
    else:
        print("\n✅ No cache files found - project is already clean!")
    
    print("\n🚀 Your project is now ready to run without cache conflicts!")

if __name__ == "__main__":
    main()