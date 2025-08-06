#!/usr/bin/env python3
"""
GitHub Integration Automation for Crypto Trading Bot
Handles automated commits, pushes, and repository management
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.agent_tools_bridge import get_agent_bridge

logger = logging.getLogger(__name__)

class GitHubIntegrationAutomation:
    """Automated GitHub operations for the crypto trading bot"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.bridge = get_agent_bridge(str(self.project_root))
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load GitHub configuration"""
        config_path = self.project_root / '.env'
        config = {
            'github_token': None,
            'github_owner': 'freshwaterbruce2',
            'github_repo': 'crypto-bot',
            'auto_commit': True,
            'auto_push': True
        }

        if config_path.exists():
            with open(config_path) as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        config['github_token'] = line.split('=', 1)[1].strip()
                    elif line.startswith('GITHUB_OWNER='):
                        config['github_owner'] = line.split('=', 1)[1].strip()
                    elif line.startswith('GITHUB_REPO='):
                        config['github_repo'] = line.split('=', 1)[1].strip()

        return config

    def check_git_status(self) -> dict[str, Any]:
        """Check current git status"""
        result = self.bridge.execute_tool('github_status')

        if result['success']:
            status_lines = result['result']['stdout'].strip().split('\n')

            # Parse git status output
            changes = {
                'modified': [],
                'added': [],
                'deleted': [],
                'untracked': []
            }

            for line in status_lines:
                if not line.strip():
                    continue

                status = line[:2]
                file_path = line[3:].strip()

                if status.startswith('M'):
                    changes['modified'].append(file_path)
                elif status.startswith('A'):
                    changes['added'].append(file_path)
                elif status.startswith('D'):
                    changes['deleted'].append(file_path)
                elif status.startswith('??'):
                    changes['untracked'].append(file_path)

            return {
                'success': True,
                'has_changes': bool(sum(len(v) for v in changes.values())),
                'changes': changes
            }

        return {
            'success': False,
            'error': result.get('error', 'Failed to check git status')
        }

    def auto_commit_changes(self, message: str = None) -> dict[str, Any]:
        """Automatically commit changes if auto_commit is enabled"""
        if not self.config.get('auto_commit', False):
            return {'success': False, 'reason': 'Auto-commit disabled'}

        # Check if there are changes to commit
        status = self.check_git_status()
        if not status['success'] or not status['has_changes']:
            return {'success': False, 'reason': 'No changes to commit'}

        # Generate commit message if not provided
        if not message:
            changes = status['changes']
            change_summary = []

            if changes['modified']:
                change_summary.append(f"Modified {len(changes['modified'])} files")
            if changes['added']:
                change_summary.append(f"Added {len(changes['added'])} files")
            if changes['deleted']:
                change_summary.append(f"Deleted {len(changes['deleted'])} files")
            if changes['untracked']:
                change_summary.append(f"Added {len(changes['untracked'])} new files")

            message = f"Automated update: {', '.join(change_summary)}"

        # Commit changes
        result = self.bridge.execute_tool('github_commit', message=message, add_all=True)

        if result['success'] and result['result']['returncode'] == 0:
            return {
                'success': True,
                'message': message,
                'commit_output': result['result']['stdout']
            }

        return {
            'success': False,
            'error': result['result']['stderr'] or 'Commit failed',
            'returncode': result['result']['returncode']
        }

    def auto_push_changes(self, branch: str = None) -> dict[str, Any]:
        """Automatically push changes if auto_push is enabled"""
        if not self.config.get('auto_push', False):
            return {'success': False, 'reason': 'Auto-push disabled'}

        # Push changes
        result = self.bridge.execute_tool('github_push', branch=branch)

        if result['success'] and result['result']['returncode'] == 0:
            return {
                'success': True,
                'push_output': result['result']['stdout']
            }

        return {
            'success': False,
            'error': result['result']['stderr'] or 'Push failed',
            'returncode': result['result']['returncode']
        }

    def sync_with_remote(self, commit_message: str = None) -> dict[str, Any]:
        """Complete sync workflow: commit and push"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'commit': None,
            'push': None,
            'overall_success': False
        }

        # Step 1: Commit changes
        commit_result = self.auto_commit_changes(commit_message)
        results['commit'] = commit_result

        if not commit_result['success']:
            if commit_result.get('reason') == 'No changes to commit':
                results['overall_success'] = True
                results['message'] = 'Repository is up to date'
            return results

        # Step 2: Push changes
        push_result = self.auto_push_changes()
        results['push'] = push_result

        results['overall_success'] = push_result['success']

        if results['overall_success']:
            results['message'] = f"Successfully synced: {commit_result['message']}"
        else:
            results['message'] = f"Commit succeeded but push failed: {push_result.get('error', 'Unknown error')}"

        return results

    def create_automated_backup(self) -> dict[str, Any]:
        """Create an automated backup commit"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Automated backup - {timestamp}"

        return self.sync_with_remote(commit_message)

    def log_automation_event(self, event_type: str, details: dict[str, Any]):
        """Log automation events"""
        log_file = self.project_root / 'automation.log'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }

        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')


def main():
    """Main entry point for GitHub automation"""
    import argparse

    parser = argparse.ArgumentParser(description='GitHub Integration Automation')
    parser.add_argument('action', choices=['status', 'commit', 'push', 'sync', 'backup'],
                       help='Action to perform')
    parser.add_argument('--message', '-m', help='Commit message')
    parser.add_argument('--branch', '-b', help='Branch to push to')
    parser.add_argument('--project-root', help='Project root directory')

    args = parser.parse_args()

    # Initialize automation
    automation = GitHubIntegrationAutomation(args.project_root)

    if args.action == 'status':
        result = automation.check_git_status()
        print(json.dumps(result, indent=2))

    elif args.action == 'commit':
        result = automation.auto_commit_changes(args.message)
        print(json.dumps(result, indent=2))
        automation.log_automation_event('commit', result)

    elif args.action == 'push':
        result = automation.auto_push_changes(args.branch)
        print(json.dumps(result, indent=2))
        automation.log_automation_event('push', result)

    elif args.action == 'sync':
        result = automation.sync_with_remote(args.message)
        print(json.dumps(result, indent=2))
        automation.log_automation_event('sync', result)

    elif args.action == 'backup':
        result = automation.create_automated_backup()
        print(json.dumps(result, indent=2))
        automation.log_automation_event('backup', result)

    return 0 if result.get('success') or result.get('overall_success') else 1


if __name__ == '__main__':
    sys.exit(main())
