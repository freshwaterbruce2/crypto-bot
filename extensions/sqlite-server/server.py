#!/usr/bin/env python3
"""
SQLite MCP Server
Provides SQLite database operations for trading data
"""

import asyncio
import os
import sqlite3

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


class SQLiteServer:
    """SQLite database server for trading data"""

    def __init__(self, db_path: str = "D:\\trading_data\\trading_bot.db"):
        self.server = Server("sqlite-server")
        self.db_path = db_path
        self.ensure_db_exists()
        self.setup_handlers()

    def ensure_db_exists(self):
        """Ensure database directory and file exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            # Create database with basic trading tables
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        fee REAL DEFAULT 0,
                        pnl REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending'
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS balances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        currency TEXT NOT NULL,
                        balance REAL NOT NULL,
                        available REAL NOT NULL,
                        reserved REAL DEFAULT 0
                    )
                ''')
                conn.commit()

    def setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available SQLite tools"""
            tools = [
                Tool(
                    name="execute_query",
                    description="Execute SQL query on trading database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL query to execute"},
                            "params": {"type": "array", "description": "Query parameters", "default": []}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="insert_trade",
                    description="Insert trade record into database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Trading symbol"},
                            "side": {"type": "string", "enum": ["buy", "sell"]},
                            "quantity": {"type": "number", "description": "Trade quantity"},
                            "price": {"type": "number", "description": "Trade price"},
                            "fee": {"type": "number", "default": 0},
                            "pnl": {"type": "number", "default": 0},
                            "status": {"type": "string", "default": "completed"}
                        },
                        "required": ["symbol", "side", "quantity", "price"]
                    }
                ),
                Tool(
                    name="get_trading_stats",
                    description="Get trading statistics and performance metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Filter by symbol (optional)"},
                            "days": {"type": "integer", "default": 30, "description": "Days to look back"}
                        }
                    }
                ),
                Tool(
                    name="update_balance",
                    description="Update balance information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "currency": {"type": "string", "description": "Currency symbol"},
                            "balance": {"type": "number", "description": "Total balance"},
                            "available": {"type": "number", "description": "Available balance"},
                            "reserved": {"type": "number", "default": 0}
                        },
                        "required": ["currency", "balance", "available"]
                    }
                )
            ]
            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            try:
                if name == "execute_query":
                    return await self.execute_query(arguments)
                elif name == "insert_trade":
                    return await self.insert_trade(arguments)
                elif name == "get_trading_stats":
                    return await self.get_trading_stats(arguments)
                elif name == "update_balance":
                    return await self.update_balance(arguments)
                else:
                    raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")
            except Exception as e:
                return CallToolResult(
                    content=[ToolMessage(content=f"Error: {str(e)}", isError=True)]
                )

    async def execute_query(self, args: dict) -> CallToolResult:
        """Execute SQL query"""
        query = args.get("query", "")
        params = args.get("params", [])

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if query.strip().upper().startswith(("SELECT", "WITH")):
                    results = cursor.fetchall()
                    columns = [description[0] for description in cursor.description]

                    output = "Query executed successfully\\n"
                    output += f"Columns: {', '.join(columns)}\\n"
                    output += f"Rows returned: {len(results)}\\n\\n"

                    if results:
                        for row in results[:50]:  # Limit to 50 rows
                            output += f"{dict(zip(columns, row))}\\n"

                    return CallToolResult(
                        content=[ToolMessage(content=output)]
                    )
                else:
                    conn.commit()
                    return CallToolResult(
                        content=[ToolMessage(content=f"Query executed successfully. Rows affected: {cursor.rowcount}")]
                    )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"SQL execution failed: {str(e)}", isError=True)]
            )

    async def insert_trade(self, args: dict) -> CallToolResult:
        """Insert trade record"""
        symbol = args.get("symbol")
        side = args.get("side")
        quantity = args.get("quantity")
        price = args.get("price")
        fee = args.get("fee", 0)
        pnl = args.get("pnl", 0)
        status = args.get("status", "completed")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades (symbol, side, quantity, price, fee, pnl, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, side, quantity, price, fee, pnl, status))
                conn.commit()

                trade_id = cursor.lastrowid
                return CallToolResult(
                    content=[ToolMessage(content=f"Trade recorded successfully. ID: {trade_id}")]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to insert trade: {str(e)}", isError=True)]
            )

    async def get_trading_stats(self, args: dict) -> CallToolResult:
        """Get trading statistics"""
        symbol = args.get("symbol")
        days = args.get("days", 30)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                where_clause = f"WHERE timestamp >= datetime('now', '-{days} days')"
                if symbol:
                    where_clause += f" AND symbol = '{symbol}'"

                # Get basic stats
                cursor.execute(f'''
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        MAX(pnl) as max_profit,
                        MIN(pnl) as max_loss,
                        SUM(fee) as total_fees
                    FROM trades {where_clause}
                ''')

                stats = cursor.fetchone()
                if stats[0] == 0:
                    return CallToolResult(
                        content=[ToolMessage(content="No trades found for the specified period")]
                    )

                total_trades, winning_trades, total_pnl, avg_pnl, max_profit, max_loss, total_fees = stats
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                output = f"=== TRADING STATISTICS ({days} days) ===\\n"
                if symbol:
                    output += f"Symbol: {symbol}\\n"
                output += f"Total Trades: {total_trades}\\n"
                output += f"Winning Trades: {winning_trades}\\n"
                output += f"Win Rate: {win_rate:.2f}%\\n"
                output += f"Total P&L: ${total_pnl:.2f}\\n"
                output += f"Average P&L: ${avg_pnl:.2f}\\n"
                output += f"Max Profit: ${max_profit:.2f}\\n"
                output += f"Max Loss: ${max_loss:.2f}\\n"
                output += f"Total Fees: ${total_fees:.2f}\\n"
                output += f"Net P&L: ${total_pnl - total_fees:.2f}"

                return CallToolResult(
                    content=[ToolMessage(content=output)]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to get trading stats: {str(e)}", isError=True)]
            )

    async def update_balance(self, args: dict) -> CallToolResult:
        """Update balance information"""
        currency = args.get("currency")
        balance = args.get("balance")
        available = args.get("available")
        reserved = args.get("reserved", 0)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO balances (currency, balance, available, reserved)
                    VALUES (?, ?, ?, ?)
                ''', (currency, balance, available, reserved))
                conn.commit()

                return CallToolResult(
                    content=[ToolMessage(content=f"Balance updated for {currency}: ${balance} (Available: ${available})")]
                )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Failed to update balance: {str(e)}", isError=True)]
            )

async def main():
    """Main entry point"""
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "D:\\trading_data\\trading_bot.db"
    sqlite_server = SQLiteServer(db_path)

    async with sqlite_server.server.stdio_client() as streams:
        await sqlite_server.server.request_loop(*streams)

if __name__ == "__main__":
    asyncio.run(main())
