#!/usr/bin/env python3
"""
Quick installation script for missing orchestrator dependencies.
Run this to fix the orchestrated mode dependency issues immediately.
"""

import importlib
import subprocess
import sys


def check_package(package_name):
    """Check if a package is installed."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")
        return False

def main():
    """Install missing dependencies for orchestrated mode."""
    print("🔧 Checking and installing missing dependencies for orchestrated mode...")

    # Critical dependencies for orchestrated mode
    missing_deps = [
        ('watchdog', 'watchdog>=3.0.0'),
        ('rich', 'rich>=13.0.0'),
        ('psutil', 'psutil>=5.9.0')
    ]

    installed = []
    failed = []

    for module_name, package_spec in missing_deps:
        print(f"\n📦 Checking {module_name}...")

        if check_package(module_name):
            print(f"✅ {module_name} is already installed")
        else:
            print(f"❌ {module_name} is missing - installing {package_spec}...")
            if install_package(package_spec):
                print(f"✅ Successfully installed {package_spec}")
                installed.append(package_spec)
            else:
                print(f"❌ Failed to install {package_spec}")
                failed.append(package_spec)

    print("\n🎯 Installation Summary:")
    if installed:
        print(f"✅ Successfully installed: {', '.join(installed)}")
    if failed:
        print(f"❌ Failed to install: {', '.join(failed)}")

    if not failed:
        print("\n🚀 All dependencies installed! Orchestrated mode should now work.")
        print("   Try running: python main.py --mode orchestrated")
    else:
        print("\n⚠️  Some dependencies failed to install. Try installing manually:")
        for pkg in failed:
            print(f"   pip install {pkg}")

if __name__ == "__main__":
    main()
