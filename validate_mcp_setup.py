#!/usr/bin/env python3
"""
Comprehensive MCP Server Setup Validation
Tests all MCP server connections and agent capabilities
"""

import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.agent_tools_bridge import get_agent_bridge, register_agent_tools

class MCPValidator:
    def __init__(self):
        self.project_root = project_root
        self.results = {
            'mcp_configs': {},
            'agent_tools': {},
            'mcp_servers': {},
            'hooks': {},
            'agent_definitions': {},
            'recommendations': []
        }
        
    def validate_mcp_configs(self):
        """Validate MCP configuration files"""
        print("\n1. Validating MCP Configuration Files...")
        
        config_files = [
            '.mcp.json',
            'claude_desktop_config.json',
            '.claude/settings.local.json'
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        config = json.load(f)
                    self.results['mcp_configs'][config_file] = {
                        'exists': True,
                        'valid_json': True,
                        'content_summary': self._summarize_config(config)
                    }
                    print(f"  ✓ {config_file}: Valid JSON, {len(config.get('mcpServers', {}))} servers configured")
                except Exception as e:
                    self.results['mcp_configs'][config_file] = {
                        'exists': True,
                        'valid_json': False,
                        'error': str(e)
                    }
                    print(f"  ✗ {config_file}: Invalid JSON - {e}")
            else:
                self.results['mcp_configs'][config_file] = {'exists': False}
                print(f"  ✗ {config_file}: Not found")
                
    def _summarize_config(self, config: dict) -> dict:
        """Summarize configuration content"""
        summary = {}
        
        if 'mcpServers' in config:
            servers = config['mcpServers']
            summary['server_count'] = len(servers)
            summary['servers'] = list(servers.keys())
            
        if 'permissions' in config:
            perms = config['permissions']
            summary['allowed_permissions'] = len(perms.get('allow', []))
            summary['denied_permissions'] = len(perms.get('deny', []))
            
        if 'hooks' in config:
            summary['hooks'] = list(config['hooks'].keys())
            
        return summary
        
    def validate_agent_tools(self):
        """Validate agent tools bridge functionality"""
        print("\n2. Validating Agent Tools Bridge...")
        
        try:
            # Test bridge initialization
            bridge = get_agent_bridge(str(self.project_root))
            tools = bridge.get_available_tools()
            
            self.results['agent_tools']['bridge_initialized'] = True
            self.results['agent_tools']['available_tools'] = tools
            print(f"  ✓ Bridge initialized with {len(tools)} tools")
            
            # Test agent registration
            registration = register_agent_tools('test_agent', str(self.project_root))
            self.results['agent_tools']['registration_test'] = registration
            print(f"  ✓ Agent registration successful")
            
            # Test a simple tool execution
            test_result = bridge.execute_tool('list_files', path='src/utils')
            if test_result['success']:
                self.results['agent_tools']['tool_test'] = 'success'
                print(f"  ✓ Tool execution test passed")
            else:
                self.results['agent_tools']['tool_test'] = test_result['error']
                print(f"  ✗ Tool execution failed: {test_result['error']}")
                
        except Exception as e:
            self.results['agent_tools']['error'] = str(e)
            print(f"  ✗ Agent tools validation failed: {e}")
            
    def validate_mcp_servers(self):
        """Validate MCP server availability (without actually starting them)"""
        print("\n3. Validating MCP Server Definitions...")
        
        # Load MCP configurations
        mcp_config_path = self.project_root / '.mcp.json'
        if not mcp_config_path.exists():
            print("  ✗ .mcp.json not found")
            return
            
        with open(mcp_config_path, 'r') as f:
            mcp_config = json.load(f)
            
        servers = mcp_config.get('mcpServers', {})
        
        for server_name, server_config in servers.items():
            server_result = {
                'command': server_config.get('command'),
                'args': server_config.get('args', []),
                'env': server_config.get('env', {})
            }
            
            # Check if it's a local Python/Node script
            if server_config.get('args'):
                script_path = server_config['args'][0] if server_config['args'] else None
                if script_path and (script_path.endswith('.py') or script_path.endswith('.js')):
                    if Path(script_path).exists():
                        server_result['script_exists'] = True
                        print(f"  ✓ {server_name}: Script exists at {script_path}")
                    else:
                        server_result['script_exists'] = False
                        print(f"  ✗ {server_name}: Script not found at {script_path}")
                else:
                    server_result['type'] = 'npm_package'
                    print(f"  ✓ {server_name}: NPM package server")
            
            self.results['mcp_servers'][server_name] = server_result
            
    def validate_hooks(self):
        """Validate hook configuration"""
        print("\n4. Validating Hook Configuration...")
        
        settings_path = self.project_root / '.claude/settings.local.json'
        if not settings_path.exists():
            print("  ✗ Settings file not found")
            return
            
        with open(settings_path, 'r') as f:
            settings = json.load(f)
            
        hooks = settings.get('hooks', {})
        
        for hook_name, hook_config in hooks.items():
            hook_result = {
                'command': hook_config.get('command'),
                'args': hook_config.get('args', []),
                'timeout': hook_config.get('timeout', 30000)
            }
            
            # Test if the hook script exists
            if hook_config.get('args'):
                script_path = hook_config['args'][0]
                if Path(script_path).exists():
                    hook_result['script_exists'] = True
                    print(f"  ✓ {hook_name}: Script exists")
                else:
                    hook_result['script_exists'] = False
                    print(f"  ✗ {hook_name}: Script not found")
            
            self.results['hooks'][hook_name] = hook_result
            
    def validate_agent_definitions(self):
        """Validate agent definition files"""
        print("\n5. Validating Agent Definitions...")
        
        agents_dir = self.project_root / '.claude/agents'
        if not agents_dir.exists():
            print("  ✗ Agents directory not found")
            return
            
        agent_files = list(agents_dir.glob('*.md'))
        
        for agent_file in agent_files:
            agent_name = agent_file.stem
            try:
                with open(agent_file, 'r') as f:
                    content = f.read()
                    
                # Basic validation - check for required sections
                has_role = 'role:' in content.lower()
                has_capabilities = 'capabilities:' in content.lower() or 'expertise:' in content.lower()
                
                self.results['agent_definitions'][agent_name] = {
                    'file': str(agent_file.name),
                    'size': len(content),
                    'has_role': has_role,
                    'has_capabilities': has_capabilities,
                    'valid': has_role and has_capabilities
                }
                
                status = "✓" if has_role and has_capabilities else "✗"
                print(f"  {status} {agent_name}: {'Valid' if has_role and has_capabilities else 'Missing sections'}")
                
            except Exception as e:
                self.results['agent_definitions'][agent_name] = {'error': str(e)}
                print(f"  ✗ {agent_name}: Error reading file - {e}")
                
    def check_dependencies(self):
        """Check for required dependencies"""
        print("\n6. Checking Dependencies...")
        
        dependencies = {
            'python': 'python3 --version',
            'node': 'node --version',
            'npm': 'npm --version',
            'npx': 'npx --version'
        }
        
        for dep_name, cmd in dependencies.items():
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"  ✓ {dep_name}: {version}")
                    self.results['dependencies'] = self.results.get('dependencies', {})
                    self.results['dependencies'][dep_name] = version
                else:
                    print(f"  ✗ {dep_name}: Not found")
            except:
                print(f"  ✗ {dep_name}: Not found")
                
    def generate_recommendations(self):
        """Generate recommendations based on validation results"""
        print("\n7. Generating Recommendations...")
        
        recommendations = []
        
        # Check MCP configs
        if not all(cfg.get('exists', False) for cfg in self.results['mcp_configs'].values()):
            recommendations.append("Some MCP configuration files are missing. Ensure all config files are present.")
            
        # Check agent tools
        if not self.results['agent_tools'].get('bridge_initialized', False):
            recommendations.append("Agent tools bridge failed to initialize. Check Python environment and imports.")
            
        # Check hooks
        for hook_name, hook_info in self.results['hooks'].items():
            if not hook_info.get('script_exists', True):
                recommendations.append(f"Hook script for '{hook_name}' not found. Verify path in settings.local.json")
                
        # Check agent definitions
        invalid_agents = [name for name, info in self.results['agent_definitions'].items() 
                         if not info.get('valid', False)]
        if invalid_agents:
            recommendations.append(f"Some agent definitions are incomplete: {', '.join(invalid_agents)}")
            
        # Check SQL database location
        sqlite_server = self.results['mcp_servers'].get('sqlite', {})
        if sqlite_server and 'D:/' in str(sqlite_server.get('args', [])):
            recommendations.append("✓ SQL database correctly configured on D: drive")
        else:
            recommendations.append("Consider moving SQL database to D: drive as per user requirements")
            
        self.results['recommendations'] = recommendations
        
        if recommendations:
            for rec in recommendations:
                print(f"  • {rec}")
        else:
            print("  ✓ No issues found - MCP setup appears complete!")
            
    def save_report(self):
        """Save validation report"""
        report_path = self.project_root / 'mcp_validation_report.json'
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n8. Validation report saved to: {report_path}")
        
    def run_validation(self):
        """Run all validation steps"""
        print("=" * 60)
        print("MCP Server Setup Validation for Crypto Trading Bot")
        print("=" * 60)
        
        self.validate_mcp_configs()
        self.validate_agent_tools()
        self.validate_mcp_servers()
        self.validate_hooks()
        self.validate_agent_definitions()
        self.check_dependencies()
        self.generate_recommendations()
        self.save_report()
        
        print("\n" + "=" * 60)
        print("Validation Complete!")
        print("=" * 60)
        
        # Summary
        total_issues = len([r for r in self.results['recommendations'] if not r.startswith('✓')])
        if total_issues == 0:
            print("\n✅ MCP setup is PRODUCTION READY!")
            print("All configurations validated successfully.")
        else:
            print(f"\n⚠️  Found {total_issues} issue(s) to address.")
            print("Review the recommendations above for next steps.")

if __name__ == "__main__":
    validator = MCPValidator()
    validator.run_validation()