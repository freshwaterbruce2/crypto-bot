#!/usr/bin/env python3
"""
Desktop Commander MCP Server for Windows 11
Provides system control, window management, and desktop automation capabilities
"""

import asyncio
import subprocess
import winreg

import psutil
import pyautogui
from mcp.server import Server
from mcp.server.models import (
    CallToolResult,
    ListToolsResult,
    Tool,
    ToolMessage,
)
from mcp.types import (
    INVALID_PARAMS,
    McpError,
)

# Initialize PyAutoGUI settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

class DesktopCommander:
    """Windows 11 Desktop Commander with advanced automation capabilities"""

    def __init__(self):
        self.server = Server("desktop-commander")
        self.setup_handlers()

    def setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available desktop commander tools"""
            tools = [
                Tool(
                    name="execute_command",
                    description="Execute Windows command or PowerShell script",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "shell": {"type": "string", "enum": ["cmd", "powershell"], "default": "cmd"},
                            "admin": {"type": "boolean", "default": False, "description": "Run as administrator"}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="list_running_processes",
                    description="List all running processes with details",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_name": {"type": "string", "description": "Filter by process name"},
                            "sort_by": {"type": "string", "enum": ["name", "cpu", "memory"], "default": "name"}
                        }
                    }
                ),
                Tool(
                    name="kill_process",
                    description="Terminate a process by name or PID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "process": {"type": "string", "description": "Process name or PID"},
                            "force": {"type": "boolean", "default": False}
                        },
                        "required": ["process"]
                    }
                ),
                Tool(
                    name="get_system_info",
                    description="Get comprehensive system information",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="manage_windows",
                    description="Manage windows (minimize, maximize, close, focus)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["list", "minimize", "maximize", "close", "focus"]},
                            "window_title": {"type": "string", "description": "Window title to target"},
                            "process_name": {"type": "string", "description": "Process name to target"}
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="automate_gui",
                    description="Automate GUI interactions (click, type, screenshot)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["click", "type", "screenshot", "key_press"]},
                            "x": {"type": "integer", "description": "X coordinate for click"},
                            "y": {"type": "integer", "description": "Y coordinate for click"},
                            "text": {"type": "string", "description": "Text to type"},
                            "key": {"type": "string", "description": "Key to press"},
                            "filename": {"type": "string", "description": "Screenshot filename"}
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="manage_services",
                    description="Manage Windows services",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["list", "start", "stop", "restart", "status"]},
                            "service_name": {"type": "string", "description": "Service name"}
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="registry_operations",
                    description="Windows Registry operations (read/write/delete)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["read", "write", "delete", "list"]},
                            "hive": {"type": "string", "enum": ["HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE", "HKEY_CLASSES_ROOT"]},
                            "key_path": {"type": "string", "description": "Registry key path"},
                            "value_name": {"type": "string", "description": "Value name"},
                            "value_data": {"type": "string", "description": "Value data to write"},
                            "value_type": {"type": "string", "enum": ["REG_SZ", "REG_DWORD"], "default": "REG_SZ"}
                        },
                        "required": ["action", "hive", "key_path"]
                    }
                ),
                Tool(
                    name="network_operations",
                    description="Network diagnostic and management operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["ping", "tracert", "netstat", "ipconfig", "dns_lookup"]},
                            "target": {"type": "string", "description": "Target hostname/IP for network operations"},
                            "options": {"type": "string", "description": "Additional command options"}
                        },
                        "required": ["action"]
                    }
                )
            ]
            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            try:
                if name == "execute_command":
                    return await self.execute_command(arguments)
                elif name == "list_running_processes":
                    return await self.list_running_processes(arguments)
                elif name == "kill_process":
                    return await self.kill_process(arguments)
                elif name == "get_system_info":
                    return await self.get_system_info()
                elif name == "manage_windows":
                    return await self.manage_windows(arguments)
                elif name == "automate_gui":
                    return await self.automate_gui(arguments)
                elif name == "manage_services":
                    return await self.manage_services(arguments)
                elif name == "registry_operations":
                    return await self.registry_operations(arguments)
                elif name == "network_operations":
                    return await self.network_operations(arguments)
                else:
                    raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")
            except Exception as e:
                return CallToolResult(
                    content=[ToolMessage(content=f"Error: {str(e)}", isError=True)]
                )

    async def execute_command(self, args: dict) -> CallToolResult:
        """Execute Windows command or PowerShell script"""
        command = args.get("command", "")
        shell = args.get("shell", "cmd")
        admin = args.get("admin", False)

        try:
            if shell == "powershell":
                if admin:
                    # Run PowerShell as admin
                    full_command = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {command}' -Verb RunAs\""
                else:
                    full_command = f"powershell -Command \"{command}\""
            else:
                if admin:
                    full_command = f"runas /user:Administrator \"{command}\""
                else:
                    full_command = command

            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = f"Exit Code: {result.returncode}\\n"
            if result.stdout:
                output += f"STDOUT:\\n{result.stdout}\\n"
            if result.stderr:
                output += f"STDERR:\\n{result.stderr}\\n"

            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Command execution failed: {str(e)}", isError=True)]
            )

    async def list_running_processes(self, args: dict) -> CallToolResult:
        """List running processes with details"""
        filter_name = args.get("filter_name", "")
        sort_by = args.get("sort_by", "name")

        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                try:
                    proc_info = proc.info
                    if filter_name and filter_name.lower() not in proc_info['name'].lower():
                        continue

                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_mb': round(proc_info['memory_info'].rss / 1024 / 1024, 2),
                        'status': proc_info['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort processes
            if sort_by == "cpu":
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            else:
                processes.sort(key=lambda x: x['name'])

            output = "Running Processes:\\n"
            output += f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'Memory(MB)':<12} {'Status':<10}\\n"
            output += "-" * 70 + "\\n"

            for proc in processes[:50]:  # Limit to top 50
                output += f"{proc['pid']:<8} {proc['name'][:24]:<25} {proc['cpu_percent']:<8} {proc['memory_mb']:<12} {proc['status']:<10}\\n"

            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to list processes: {str(e)}", isError=True)]
            )

    async def kill_process(self, args: dict) -> CallToolResult:
        """Kill a process by name or PID"""
        process = args.get("process", "")
        force = args.get("force", False)

        try:
            if process.isdigit():
                # Kill by PID
                pid = int(process)
                proc = psutil.Process(pid)
                proc_name = proc.name()

                if force:
                    proc.kill()
                else:
                    proc.terminate()

                return CallToolResult(
                    content=[ToolMessage(content=f"Process {proc_name} (PID: {pid}) terminated successfully")]
                )
            else:
                # Kill by name
                killed_count = 0
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'].lower() == process.lower():
                        try:
                            if force:
                                proc.kill()
                            else:
                                proc.terminate()
                            killed_count += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                if killed_count > 0:
                    return CallToolResult(
                        content=[ToolMessage(content=f"Terminated {killed_count} process(es) named '{process}'")]
                    )
                else:
                    return CallToolResult(
                        content=[ToolMessage(content=f"No processes found with name '{process}'")]
                    )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to kill process: {str(e)}", isError=True)]
            )

    async def get_system_info(self) -> CallToolResult:
        """Get comprehensive system information"""
        try:
            # System info
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Network info
            network = psutil.net_io_counters()

            # Boot time
            boot_time = psutil.boot_time()

            output = "=== SYSTEM INFORMATION ===\\n"
            output += f"CPU Cores: {cpu_count}\\n"
            output += f"CPU Usage: {cpu_percent}%\\n"
            output += f"Memory Total: {round(memory.total / 1024**3, 2)} GB\\n"
            output += f"Memory Available: {round(memory.available / 1024**3, 2)} GB\\n"
            output += f"Memory Usage: {memory.percent}%\\n"
            output += f"Disk Total: {round(disk.total / 1024**3, 2)} GB\\n"
            output += f"Disk Free: {round(disk.free / 1024**3, 2)} GB\\n"
            output += f"Disk Usage: {round(disk.used / disk.total * 100, 2)}%\\n"
            output += f"Network Sent: {round(network.bytes_sent / 1024**2, 2)} MB\\n"
            output += f"Network Received: {round(network.bytes_recv / 1024**2, 2)} MB\\n"
            output += f"Boot Time: {boot_time}\\n"

            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to get system info: {str(e)}", isError=True)]
            )

    async def manage_windows(self, args: dict) -> CallToolResult:
        """Manage windows"""
        action = args.get("action", "list")
        window_title = args.get("window_title", "")
        process_name = args.get("process_name", "")

        try:
            if action == "list":
                # Use PowerShell to list windows
                cmd = "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object ProcessName, MainWindowTitle, Id"
                result = subprocess.run(
                    f"powershell -Command \"{cmd}\"",
                    shell=True,
                    capture_output=True,
                    text=True
                )

                return CallToolResult(
                    content=[ToolMessage(content=f"Active Windows:\\n{result.stdout}")]
                )
            else:
                # Window management requires additional Windows API calls
                return CallToolResult(
                    content=[ToolMessage(content=f"Window management action '{action}' not yet implemented")]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Window management failed: {str(e)}", isError=True)]
            )

    async def automate_gui(self, args: dict) -> CallToolResult:
        """Automate GUI interactions"""
        action = args.get("action")

        try:
            if action == "screenshot":
                filename = args.get("filename", "screenshot.png")
                screenshot = pyautogui.screenshot()
                screenshot.save(filename)
                return CallToolResult(
                    content=[ToolMessage(content=f"Screenshot saved as {filename}")]
                )
            elif action == "click":
                x = args.get("x")
                y = args.get("y")
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    return CallToolResult(
                        content=[ToolMessage(content=f"Clicked at ({x}, {y})")]
                    )
                else:
                    return CallToolResult(
                        content=[ToolMessage(content="X and Y coordinates required for click", isError=True)]
                    )
            elif action == "type":
                text = args.get("text", "")
                pyautogui.typewrite(text)
                return CallToolResult(
                    content=[ToolMessage(content=f"Typed: {text}")]
                )
            elif action == "key_press":
                key = args.get("key", "")
                pyautogui.press(key)
                return CallToolResult(
                    content=[ToolMessage(content=f"Pressed key: {key}")]
                )
            else:
                return CallToolResult(
                    content=[ToolMessage(content=f"Unknown GUI action: {action}", isError=True)]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"GUI automation failed: {str(e)}", isError=True)]
            )

    async def manage_services(self, args: dict) -> CallToolResult:
        """Manage Windows services"""
        action = args.get("action", "list")
        service_name = args.get("service_name", "")

        try:
            if action == "list":
                cmd = "Get-Service | Select-Object Name, Status, DisplayName"
                result = subprocess.run(
                    f"powershell -Command \"{cmd}\"",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                return CallToolResult(
                    content=[ToolMessage(content=f"Windows Services:\\n{result.stdout}")]
                )
            elif action in ["start", "stop", "restart"]:
                if not service_name:
                    return CallToolResult(
                        content=[ToolMessage(content="Service name required", isError=True)]
                    )

                if action == "start":
                    cmd = f"Start-Service -Name '{service_name}'"
                elif action == "stop":
                    cmd = f"Stop-Service -Name '{service_name}'"
                else:  # restart
                    cmd = f"Restart-Service -Name '{service_name}'"

                result = subprocess.run(
                    f"powershell -Command \"{cmd}\"",
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    return CallToolResult(
                        content=[ToolMessage(content=f"Service '{service_name}' {action}ed successfully")]
                    )
                else:
                    return CallToolResult(
                        content=[ToolMessage(content=f"Failed to {action} service: {result.stderr}", isError=True)]
                    )
            else:
                return CallToolResult(
                    content=[ToolMessage(content=f"Unknown service action: {action}", isError=True)]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Service management failed: {str(e)}", isError=True)]
            )

    async def registry_operations(self, args: dict) -> CallToolResult:
        """Windows Registry operations"""
        action = args.get("action")
        hive = args.get("hive")
        key_path = args.get("key_path")
        value_name = args.get("value_name", "")
        value_data = args.get("value_data", "")

        try:
            # Map hive names to winreg constants
            hive_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT
            }

            if hive not in hive_map:
                return CallToolResult(
                    content=[ToolMessage(content=f"Invalid hive: {hive}", isError=True)]
                )

            hive_key = hive_map[hive]

            if action == "read":
                with winreg.OpenKey(hive_key, key_path) as key:
                    if value_name:
                        value, value_type = winreg.QueryValueEx(key, value_name)
                        return CallToolResult(
                            content=[ToolMessage(content=f"Value: {value} (Type: {value_type})")]
                        )
                    else:
                        # List all values
                        values = []
                        i = 0
                        try:
                            while True:
                                name, value, value_type = winreg.EnumValue(key, i)
                                values.append(f"{name}: {value} (Type: {value_type})")
                                i += 1
                        except OSError:
                            pass

                        return CallToolResult(
                            content=[ToolMessage(content="Registry Values:\\n" + "\\n".join(values))]
                        )

            elif action == "write":
                if not value_name or not value_data:
                    return CallToolResult(
                        content=[ToolMessage(content="Value name and data required for write", isError=True)]
                    )

                with winreg.OpenKey(hive_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value_data)

                return CallToolResult(
                    content=[ToolMessage(content=f"Registry value '{value_name}' set successfully")]
                )

            else:
                return CallToolResult(
                    content=[ToolMessage(content=f"Registry operation '{action}' not implemented", isError=True)]
                )

        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Registry operation failed: {str(e)}", isError=True)]
            )

    async def network_operations(self, args: dict) -> CallToolResult:
        """Network diagnostic operations"""
        action = args.get("action")
        target = args.get("target", "")
        options = args.get("options", "")

        try:
            if action == "ping":
                cmd = f"ping {options} {target}" if target else "ping 8.8.8.8"
            elif action == "tracert":
                cmd = f"tracert {options} {target}" if target else "tracert 8.8.8.8"
            elif action == "netstat":
                cmd = f"netstat {options}" if options else "netstat -an"
            elif action == "ipconfig":
                cmd = f"ipconfig {options}" if options else "ipconfig /all"
            elif action == "dns_lookup":
                cmd = f"nslookup {target}" if target else "nslookup"
            else:
                return CallToolResult(
                    content=[ToolMessage(content=f"Unknown network action: {action}", isError=True)]
                )

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = f"Command: {cmd}\\n"
            output += f"Exit Code: {result.returncode}\\n"
            if result.stdout:
                output += f"Output:\\n{result.stdout}"
            if result.stderr:
                output += f"Error:\\n{result.stderr}"

            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Network operation failed: {str(e)}", isError=True)]
            )

async def main():
    """Main entry point"""
    desktop_commander = DesktopCommander()

    # Read server capabilities from stdin
    async with desktop_commander.server.stdio_client() as streams:
        await desktop_commander.server.request_loop(*streams)

if __name__ == "__main__":
    asyncio.run(main())
