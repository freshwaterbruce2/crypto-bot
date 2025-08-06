"""
Agent Tools Bridge
Provides MCP claude-flow agents with the same file access capabilities as Claude Code
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class AgentToolsBridge:
    """Bridge to give MCP agents full file system access like Claude Code"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.tools_available = {
            'read_file': self.read_file,
            'write_file': self.write_file,
            'edit_file': self.edit_file,
            'multi_edit_file': self.multi_edit_file,
            'bash_command': self.bash_command,
            'list_files': self.list_files,
            'glob_search': self.glob_search,
            'grep_search': self.grep_search,
            'create_directory': self.create_directory,
            'delete_file': self.delete_file,
            'move_file': self.move_file,
            'copy_file': self.copy_file,
            'github_commit': self.github_commit,
            'github_push': self.github_push,
            'github_status': self.github_status
        }

    def get_available_tools(self) -> list[str]:
        """Get list of available tools for agents"""
        return list(self.tools_available.keys())

    def execute_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute a tool with given parameters"""
        try:
            if tool_name not in self.tools_available:
                return {
                    'success': False,
                    'error': f'Tool {tool_name} not available',
                    'available_tools': self.get_available_tools()
                }

            result = self.tools_available[tool_name](**kwargs)
            return {
                'success': True,
                'result': result,
                'tool': tool_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'tool': tool_name
            }

    def read_file(self, file_path: str, offset: int = None, limit: int = None) -> str:
        """Read file content (equivalent to Claude Code Read tool)"""
        full_path = self.project_root / file_path

        try:
            with open(full_path, encoding='utf-8') as f:
                if offset is not None:
                    # Skip to offset line
                    for _ in range(offset):
                        f.readline()

                if limit is not None:
                    # Read limited lines
                    lines = []
                    for i in range(limit):
                        line = f.readline()
                        if not line:
                            break
                        line_num = (offset or 0) + i + 1
                        lines.append(f"{line_num:5d}→{line.rstrip()}")
                    return '\n'.join(lines)
                else:
                    # Read all lines with line numbers
                    lines = f.readlines()
                    start_line = (offset or 0) + 1
                    numbered_lines = [
                        f"{start_line + i:5d}→{line.rstrip()}"
                        for i, line in enumerate(lines)
                    ]
                    return '\n'.join(numbered_lines)
        except Exception as e:
            raise Exception(f"Error reading {file_path}: {e}")

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to file (equivalent to Claude Code Write tool)"""
        full_path = self.project_root / file_path

        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"File written successfully: {file_path}"
        except Exception as e:
            raise Exception(f"Error writing {file_path}: {e}")

    def edit_file(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Edit file by replacing text (equivalent to Claude Code Edit tool)"""
        full_path = self.project_root / file_path

        try:
            with open(full_path, encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                raise Exception(f"String not found in {file_path}: {old_string[:100]}...")

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return f"File edited successfully: {file_path}"
        except Exception as e:
            raise Exception(f"Error editing {file_path}: {e}")

    def multi_edit_file(self, file_path: str, edits: list[dict[str, Any]]) -> str:
        """Perform multiple edits on a file (equivalent to Claude Code MultiEdit tool)"""
        full_path = self.project_root / file_path

        try:
            with open(full_path, encoding='utf-8') as f:
                content = f.read()

            # Apply edits in sequence
            for edit in edits:
                old_string = edit['old_string']
                new_string = edit['new_string']
                replace_all = edit.get('replace_all', False)

                if old_string not in content:
                    raise Exception(f"String not found: {old_string[:100]}...")

                if replace_all:
                    content = content.replace(old_string, new_string)
                else:
                    content = content.replace(old_string, new_string, 1)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"File multi-edited successfully: {file_path} ({len(edits)} edits)"
        except Exception as e:
            raise Exception(f"Error multi-editing {file_path}: {e}")

    def bash_command(self, command: str, timeout: int = 120) -> dict[str, Any]:
        """Execute bash command (equivalent to Claude Code Bash tool)"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )

            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': command
            }
        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'returncode': -1,
                'command': command
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'command': command
            }

    def list_files(self, path: str = ".", ignore: list[str] = None) -> list[str]:
        """List files in directory (equivalent to Claude Code LS tool)"""
        full_path = self.project_root / path
        ignore = ignore or []

        try:
            items = []
            for item in full_path.iterdir():
                # Check ignore patterns
                if any(item.match(pattern) for pattern in ignore):
                    continue

                if item.is_file():
                    items.append(f"- {item.name}")
                elif item.is_dir():
                    items.append(f"- {item.name}/")

            return sorted(items)
        except Exception as e:
            raise Exception(f"Error listing {path}: {e}")

    def glob_search(self, pattern: str, path: str = ".") -> list[str]:
        """Search files by pattern (equivalent to Claude Code Glob tool)"""
        full_path = self.project_root / path

        try:
            matches = list(full_path.glob(pattern))
            return [str(match.relative_to(self.project_root)) for match in matches]
        except Exception as e:
            raise Exception(f"Error globbing {pattern}: {e}")

    def grep_search(self, pattern: str, path: str = ".", file_type: str = None,
                   case_insensitive: bool = False, context_lines: int = 0) -> list[dict[str, Any]]:
        """Search text in files (equivalent to Claude Code Grep tool)"""
        try:
            # Build ripgrep command
            cmd = ['rg']

            if case_insensitive:
                cmd.append('-i')

            if context_lines > 0:
                cmd.extend(['-C', str(context_lines)])

            if file_type:
                cmd.extend(['--type', file_type])

            cmd.extend(['--json', pattern, path])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Parse JSON output
            import json
            matches = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        if data.get('type') == 'match':
                            matches.append({
                                'file': data['data']['path']['text'],
                                'line': data['data']['line_number'],
                                'text': data['data']['lines']['text']
                            })
                    except json.JSONDecodeError:
                        continue

            return matches
        except Exception as e:
            raise Exception(f"Error grepping {pattern}: {e}")

    def create_directory(self, path: str) -> str:
        """Create directory"""
        full_path = self.project_root / path

        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return f"Directory created: {path}"
        except Exception as e:
            raise Exception(f"Error creating directory {path}: {e}")

    def delete_file(self, path: str) -> str:
        """Delete file or directory"""
        full_path = self.project_root / path

        try:
            if full_path.is_file():
                full_path.unlink()
                return f"File deleted: {path}"
            elif full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
                return f"Directory deleted: {path}"
            else:
                return f"Path not found: {path}"
        except Exception as e:
            raise Exception(f"Error deleting {path}: {e}")

    def move_file(self, src: str, dst: str) -> str:
        """Move/rename file"""
        src_path = self.project_root / src
        dst_path = self.project_root / dst

        try:
            # Create parent directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dst_path)
            return f"Moved: {src} -> {dst}"
        except Exception as e:
            raise Exception(f"Error moving {src} to {dst}: {e}")

    def copy_file(self, src: str, dst: str) -> str:
        """Copy file"""
        src_path = self.project_root / src
        dst_path = self.project_root / dst

        try:
            import shutil
            # Create parent directory if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            return f"Copied: {src} -> {dst}"
        except Exception as e:
            raise Exception(f"Error copying {src} to {dst}: {e}")

    def github_status(self) -> dict[str, Any]:
        """Get git status (equivalent to git status)"""
        return self.bash_command("git status --porcelain")

    def github_commit(self, message: str, add_all: bool = True) -> dict[str, Any]:
        """Commit changes to git with Claude Code signature"""
        try:
            commands = []

            if add_all:
                commands.append("git add .")

            # Create commit with Claude Code signature
            commit_msg = f"""{message}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            # Use heredoc for proper multi-line commit message
            commit_cmd = f'''git commit -m "$(cat <<'EOF'
{commit_msg}
EOF
)"'''
            commands.append(commit_cmd)

            results = []
            for cmd in commands:
                result = self.bash_command(cmd)
                results.append(result)

                # If any command fails, return the failure
                if result.get('returncode', 0) != 0:
                    return result

            return {
                'stdout': '\n'.join([r.get('stdout', '') for r in results]),
                'stderr': '\n'.join([r.get('stderr', '') for r in results]),
                'returncode': 0,
                'command': 'github_commit'
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'command': 'github_commit'
            }

    def github_push(self, branch: str = None) -> dict[str, Any]:
        """Push changes to GitHub"""
        cmd = "git push"
        if branch:
            cmd += f" origin {branch}"

        return self.bash_command(cmd)


# Global bridge instance
_bridge = None

def get_agent_bridge(project_root: str = None) -> AgentToolsBridge:
    """Get or create agent tools bridge"""
    global _bridge

    if _bridge is None:
        _bridge = AgentToolsBridge(project_root)

    return _bridge

def register_agent_tools(agent_id: str, project_root: str = None) -> dict[str, Any]:
    """Register full file system tools for an agent"""
    bridge = get_agent_bridge(project_root)

    return {
        'agent_id': agent_id,
        'tools_registered': bridge.get_available_tools(),
        'bridge_ready': True,
        'capabilities': [
            'Full file system access',
            'Bash command execution',
            'File reading/writing/editing',
            'Directory operations',
            'Search and pattern matching',
            'Git and GitHub operations',
            'Automated commits with Claude Code signature'
        ]
    }

def execute_agent_tool(agent_id: str, tool_name: str, **kwargs) -> dict[str, Any]:
    """Execute a tool on behalf of an agent"""
    bridge = get_agent_bridge()

    result = bridge.execute_tool(tool_name, **kwargs)
    result['agent_id'] = agent_id
    result['timestamp'] = __import__('time').time()

    return result

# Hook integration functions
def handle_pre_task_hook(*args):
    """Handle pre-task automation hook"""
    try:
        # Log the incoming task
        task_info = {
            'timestamp': __import__('time').time(),
            'agent_id': 'automation-hook',
            'phase': 'pre-task',
            'args': args
        }

        logger.info(f"Pre-task hook triggered: {task_info}")
        return True
    except Exception as e:
        logger.error(f"Pre-task hook error: {e}")
        return False

def handle_post_task_hook(*args):
    """Handle post-task automation hook"""
    try:
        # Check if we should auto-sync with GitHub
        should_sync = _should_auto_sync()

        if should_sync:
            # Import and run GitHub automation
            automation_script = Path(__file__).parent.parent.parent / 'automation' / 'github_integration.py'

            if automation_script.exists():
                result = subprocess.run([
                    'python3', str(automation_script), 'sync',
                    '--message', 'Automated sync from agent task completion'
                ], capture_output=True, text=True, cwd=str(automation_script.parent.parent))

                logger.info(f"Auto-sync result: {result.returncode}")
                if result.stdout:
                    logger.info(f"Auto-sync output: {result.stdout}")
                if result.stderr and result.returncode != 0:
                    logger.error(f"Auto-sync error: {result.stderr}")

        return True
    except Exception as e:
        logger.error(f"Post-task hook error: {e}")
        return False

def _should_auto_sync() -> bool:
    """Determine if we should auto-sync with GitHub"""
    # Check for significant changes or time-based triggers
    # This is a simple implementation - can be enhanced based on needs

    try:
        bridge = get_agent_bridge()
        status_result = bridge.execute_tool('github_status')

        if status_result['success']:
            # If there are changes, sync them
            status_output = status_result['result']['stdout'].strip()
            return bool(status_output)  # True if there are changes

        return False
    except:
        return False

# Entry point for hook scripts
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'pre-task':
            handle_pre_task_hook(*sys.argv[2:])
        elif sys.argv[1] == 'post-task':
            handle_post_task_hook(*sys.argv[2:])
        else:
            print(f"Unknown hook: {sys.argv[1]}")
            sys.exit(1)
    else:
        print("Usage: agent_tools_bridge.py [pre-task|post-task] [args...]")
        sys.exit(1)
