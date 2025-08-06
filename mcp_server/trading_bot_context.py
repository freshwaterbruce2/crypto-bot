#!/usr/bin/env python3
"""
Trading Bot Context MCP Server
Provides trading bot context and information to Claude Desktop
"""
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TradingBotContextServer:
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
                        "name": "trading-bot-context",
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
                            "name": "get_bot_status",
                            "description": "Get current trading bot status",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_trading_config",
                            "description": "Get current trading configuration",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_project_info",
                            "description": "Get project structure and information",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }

        elif method == 'tools/call':
            tool_name = request.get('params', {}).get('name')

            if tool_name == 'get_bot_status':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "Trading Bot Status: Ready for profit generation\n" +
                                       "Strategy: Quick scalping ($1.00 -> $1.10)\n" +
                                       "Exchange: Kraken\n" +
                                       "Fee-free trading: Enabled"
                            }
                        ]
                    }
                }

            elif tool_name == 'get_trading_config':
                config_path = self.project_root / 'config.json'
                if config_path.exists():
                    with open(config_path) as f:
                        config = json.load(f)
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get('id'),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Trading Configuration:\n{json.dumps(config, indent=2)}"
                                }
                            ]
                        }
                    }

            elif tool_name == 'get_project_info':
                return {
                    "jsonrpc": "2.0",
                    "id": request.get('id'),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Project Root: {self.project_root}\n" +
                                       "Key Directories:\n" +
                                       "- src/: Main source code\n" +
                                       "- config/: Configuration files\n" +
                                       "- logs/: Trading logs\n" +
                                       "- data/: Historical data\n" +
                                       "Current Focus: Fix nonce errors and implement profit strategy"
                            }
                        ]
                    }
                }

        return {
            "jsonrpc": "2.0",
            "id": request.get('id'),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

async def main():
    server = TradingBotContextServer()

    # Send initialization complete
    print('{"jsonrpc": "2.0", "method": "initialized"}', flush=True)

    # Read from stdin
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            try:
                request = json.loads(line.strip())
                response = await server.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)

        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    asyncio.run(main())
