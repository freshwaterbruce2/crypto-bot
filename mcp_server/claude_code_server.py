#!/usr/bin/env python3
"""
Claude Code MCP Server for Windows
Provides code execution and file manipulation capabilities
"""
import json
import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ClaudeCodeServer:
    def __init__(self):
        self.project_root = project_root
        
    async def handle_request(self, request):
        """Handle incoming JSON-RPC requests"""
        method = request.get('method', '')
        
        if method == 'initialize':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {
                            "listTools": {},
                            "callTool": {}
                        }
                    },
                    "serverInfo": {
                        "name": "claude-code-server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == 'tools/list':
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "tools": [
                        {
                            "name": "execute_python",
                            "description": "Execute Python code in the trading bot environment",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Python code to execute"
                                    }
                                },
                                "required": ["code"]
                            }
                        },
                        {
                            "name": "read_file",
                            "description": "Read file contents from the project",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Relative path from project root"
                                    }
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "write_file",
                            "description": "Write content to a file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Relative path from project root"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Content to write"
                                    }
                                },
                                "required": ["path", "content"]
                            }
                        },
                        {
                            "name": "run_bot_command",
                            "description": "Run trading bot specific commands",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "Command to run (start, stop, status, test)"
                                    }
                                },
                                "required": ["command"]
                            }
                        }
                    ]
                }
            }
        
        elif method == 'tools/call':
            return await self.handle_tool_call(request)
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    async def handle_tool_call(self, request):
        """Handle tool execution requests"""
        params = request.get('params', {})
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        try:
            if tool_name == 'execute_python':
                result = await self.execute_python(arguments.get('code', ''))
            elif tool_name == 'read_file':
                result = await self.read_file(arguments.get('path', ''))
            elif tool_name == 'write_file':
                result = await self.write_file(
                    arguments.get('path', ''),
                    arguments.get('content', '')
                )
            elif tool_name == 'run_bot_command':
                result = await self.run_bot_command(arguments.get('command', ''))
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get('id'),
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def execute_python(self, code):
        """Execute Python code and return results"""
        try:
            # Create a temporary file to execute
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute the code
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            
            # Clean up
            os.unlink(temp_file)
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def read_file(self, path):
        """Read file contents"""
        try:
            file_path = self.project_root / path
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {"content": content, "path": str(file_path)}
        except Exception as e:
            return {"error": str(e)}
    
    async def write_file(self, path, content):
        """Write content to file"""
        try:
            file_path = self.project_root / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"success": True, "path": str(file_path)}
        except Exception as e:
            return {"error": str(e)}
    
    async def run_bot_command(self, command):
        """Run trading bot specific commands"""
        try:
            if command == "start":
                # Start the bot
                script_path = self.project_root / "main.py"
                if script_path.exists():
                    subprocess.Popen(
                        [sys.executable, str(script_path)],
                        cwd=str(self.project_root)
                    )
                    return {"status": "Bot starting..."}
                else:
                    return {"error": "main.py not found"}
            
            elif command == "status":
                # Check if bot is running
                # This is a simple check - you might want to implement a more robust method
                return {"status": "Bot status check not fully implemented"}
            
            elif command == "stop":
                # Stop the bot - implement based on your bot's architecture
                return {"status": "Bot stop command not fully implemented"}
            
            elif command == "test":
                # Run tests
                test_path = self.project_root / "test_main.py"
                if test_path.exists():
                    result = subprocess.run(
                        [sys.executable, str(test_path)],
                        capture_output=True,
                        text=True,
                        cwd=str(self.project_root)
                    )
                    return {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                else:
                    return {"error": "test_main.py not found"}
            
            else:
                return {"error": f"Unknown command: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def run(self):
        """Main server loop"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line)
                response = await self.handle_request(request)
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

if __name__ == "__main__":
    server = ClaudeCodeServer()
    asyncio.run(server.run())
