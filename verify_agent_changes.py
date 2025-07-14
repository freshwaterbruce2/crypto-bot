#!/usr/bin/env python3
"""
Agent Change Verification System
Ensures agents make real file changes, not fake reports
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

class AgentChangeVerifier:
    """Verify agents actually make file changes"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.baseline_file = self.project_root / "agent_baseline.json"
        
    def create_baseline(self):
        """Create baseline of current file states"""
        print("📸 Creating baseline snapshot of all files...")
        
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "files": {}
        }
        
        # Key files to monitor
        key_files = [
            "src/trading/unified_balance_manager.py",
            "src/exchange/native_kraken_exchange.py", 
            "src/core/bot.py",
            "config.json",
            "src/config/trading.py",
            "force_balance_refresh.py"
        ]
        
        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    content = f.read()
                    baseline["files"][file_path] = {
                        "hash": hashlib.md5(content).hexdigest(),
                        "size": len(content),
                        "modified": os.path.getmtime(full_path)
                    }
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} (not found)")
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        print(f"📁 Baseline saved: {len(baseline['files'])} files")
        return baseline
    
    def verify_changes(self):
        """Verify if files actually changed since baseline"""
        if not self.baseline_file.exists():
            print("❌ No baseline found - run create_baseline() first")
            return False
        
        with open(self.baseline_file, 'r') as f:
            baseline = json.load(f)
        
        print("🔍 Verifying agent changes against baseline...")
        changes_found = 0
        
        for file_path, baseline_info in baseline["files"].items():
            full_path = self.project_root / file_path
            
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    content = f.read()
                    current_hash = hashlib.md5(content).hexdigest()
                    current_size = len(content)
                    current_modified = os.path.getmtime(full_path)
                
                if current_hash != baseline_info["hash"]:
                    print(f"  ✅ CHANGED: {file_path}")
                    print(f"     Size: {baseline_info['size']} → {current_size}")
                    print(f"     Modified: {datetime.fromtimestamp(current_modified)}")
                    changes_found += 1
                else:
                    print(f"  ⚪ UNCHANGED: {file_path}")
            else:
                print(f"  ❌ MISSING: {file_path}")
        
        print(f"\n📊 SUMMARY: {changes_found} files actually changed")
        return changes_found > 0
    
    def test_agent_bridge(self):
        """Test that agent tools bridge can make real changes"""
        print("🧪 Testing agent tools bridge functionality...")
        
        test_file = self.project_root / "agent_bridge_test.txt"
        test_content = f"Agent bridge test: {datetime.now().isoformat()}"
        
        # Use agent tools bridge to create file
        try:
            from src.utils.agent_tools_bridge import execute_agent_tool
            
            result = execute_agent_tool(
                "test_agent",
                "write_file", 
                file_path="agent_bridge_test.txt",
                content=test_content
            )
            
            if result['success'] and test_file.exists():
                print("  ✅ Agent bridge can create files")
                
                # Test reading
                read_result = execute_agent_tool(
                    "test_agent",
                    "read_file",
                    file_path="agent_bridge_test.txt"
                )
                
                if read_result['success'] and test_content in read_result['result']:
                    print("  ✅ Agent bridge can read files")
                    
                    # Clean up
                    test_file.unlink()
                    print("  ✅ Agent bridge test passed")
                    return True
                else:
                    print("  ❌ Agent bridge read failed")
            else:
                print("  ❌ Agent bridge write failed")
                
        except Exception as e:
            print(f"  ❌ Agent bridge test failed: {e}")
        
        return False

def main():
    """Main verification function"""
    verifier = AgentChangeVerifier("/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025")
    
    print("🔧 AGENT CHANGE VERIFICATION SYSTEM")
    print("=" * 50)
    
    # Test agent bridge
    if verifier.test_agent_bridge():
        print("\n✅ Agent tools bridge is functional")
    else:
        print("\n❌ Agent tools bridge has issues")
        return
    
    # Create baseline
    verifier.create_baseline()
    
    print("\n✅ ALL INSTANCES STOPPED")
    print("✅ VERIFICATION SYSTEM READY")
    print("\nNow agents can be tested against this baseline to ensure real changes.")

if __name__ == '__main__':
    main()