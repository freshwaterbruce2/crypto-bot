#!/usr/bin/env python3
"""
Time Utilities MCP Server
Provides time, timezone, and scheduling utilities for trading
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
import time
import pytz
from typing import Any, Dict, List, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.models import (
    CallToolRequestParams,
    CallToolResult,
    EmptyResult,
    ListToolsResult,
    Tool,
    ToolMessage,
)
from mcp.types import (
    INVALID_PARAMS,
    INTERNAL_ERROR,
    JSONRPCError,
    McpError,
)

class TimeServer:
    """Time utilities server for trading operations"""
    
    def __init__(self):
        self.server = Server("time-server")
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available time tools"""
            tools = [
                Tool(
                    name="get_current_time",
                    description="Get current time in various formats and timezones",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "timezone": {"type": "string", "default": "UTC", "description": "Timezone (e.g., UTC, US/Eastern, Europe/London)"},
                            "format": {"type": "string", "default": "iso", "description": "Output format (iso, timestamp, readable)"}
                        }
                    }
                ),
                Tool(
                    name="market_hours",
                    description="Check if markets are open and get trading hours",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "market": {"type": "string", "enum": ["crypto", "forex", "stock_us", "stock_eu"], "default": "crypto"},
                            "timezone": {"type": "string", "default": "UTC"}
                        }
                    }
                ),
                Tool(
                    name="time_until",
                    description="Calculate time until a specific event or time",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_time": {"type": "string", "description": "Target time (ISO format or readable)"},
                            "timezone": {"type": "string", "default": "UTC"}
                        },
                        "required": ["target_time"]
                    }
                ),
                Tool(
                    name="trading_session_info",
                    description="Get current trading session information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "timezone": {"type": "string", "default": "UTC"}
                        }
                    }
                ),
                Tool(
                    name="candle_time_info",
                    description="Get information about current candle timing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "timeframe": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "4h", "1d"], "default": "15m"},
                            "timezone": {"type": "string", "default": "UTC"}
                        }
                    }
                ),
                Tool(
                    name="schedule_reminder",
                    description="Calculate optimal timing for trading activities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "activity": {"type": "string", "description": "Trading activity to schedule"},
                            "preferred_time": {"type": "string", "description": "Preferred time or 'auto'"},
                            "market_consideration": {"type": "boolean", "default": True}
                        },
                        "required": ["activity"]
                    }
                )
            ]
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            try:
                if name == "get_current_time":
                    return await self.get_current_time(arguments)
                elif name == "market_hours":
                    return await self.market_hours(arguments)
                elif name == "time_until":
                    return await self.time_until(arguments)
                elif name == "trading_session_info":
                    return await self.trading_session_info(arguments)
                elif name == "candle_time_info":
                    return await self.candle_time_info(arguments)
                elif name == "schedule_reminder":
                    return await self.schedule_reminder(arguments)
                else:
                    raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")
            except Exception as e:
                return CallToolResult(
                    content=[ToolMessage(content=f"Error: {str(e)}", isError=True)]
                )
    
    async def get_current_time(self, args: dict) -> CallToolResult:
        """Get current time in various formats"""
        timezone_str = args.get("timezone", "UTC")
        format_type = args.get("format", "iso")
        
        try:
            if timezone_str == "UTC":
                tz = pytz.UTC
            else:
                tz = pytz.timezone(timezone_str)
            
            now = datetime.now(tz)
            
            output = f"=== CURRENT TIME ===\\n"
            output += f"Timezone: {timezone_str}\\n"
            
            if format_type == "iso":
                output += f"ISO Format: {now.isoformat()}\\n"
            elif format_type == "timestamp":
                output += f"Unix Timestamp: {int(now.timestamp())}\\n"
            elif format_type == "readable":
                output += f"Readable: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\\n"
            else:
                output += f"ISO Format: {now.isoformat()}\\n"
                output += f"Unix Timestamp: {int(now.timestamp())}\\n"
                output += f"Readable: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\\n"
            
            output += f"\\nOther Timezones:\\n"
            output += f"UTC: {datetime.now(pytz.UTC).strftime('%H:%M:%S')}\\n"
            output += f"NY: {datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')}\\n"
            output += f"London: {datetime.now(pytz.timezone('Europe/London')).strftime('%H:%M:%S')}\\n"
            output += f"Tokyo: {datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')}"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Time calculation failed: {str(e)}", isError=True)]
            )
    
    async def market_hours(self, args: dict) -> CallToolResult:
        """Check market hours and status"""
        market = args.get("market", "crypto")
        timezone_str = args.get("timezone", "UTC")
        
        try:
            now = datetime.now(pytz.UTC)
            
            if market == "crypto":
                is_open = True
                status = "24/7 Trading"
                next_event = "No scheduled closures"
            elif market == "forex":
                # Forex is closed on weekends
                weekday = now.weekday()
                if weekday >= 5:  # Saturday or Sunday
                    is_open = False
                    status = "Closed (Weekend)"
                    # Calculate next Monday
                    days_until_monday = (7 - weekday) % 7
                    next_monday = now + timedelta(days=days_until_monday)
                    next_event = f"Opens Monday at 22:00 UTC ({next_monday.strftime('%Y-%m-%d')})"
                else:
                    is_open = True
                    status = "Open (24/5 Trading)"
                    next_event = "Closes Friday 22:00 UTC"
            elif market == "stock_us":
                # US Stock Market (9:30 AM - 4:00 PM ET)
                et_tz = pytz.timezone('America/New_York')
                now_et = now.astimezone(et_tz)
                
                if now_et.weekday() >= 5:  # Weekend
                    is_open = False
                    status = "Closed (Weekend)"
                    next_event = "Opens Monday 9:30 AM ET"
                elif 9.5 <= now_et.hour + now_et.minute/60 <= 16:
                    is_open = True
                    status = "Open"
                    next_event = "Closes 4:00 PM ET"
                else:
                    is_open = False
                    status = "Closed"
                    next_event = "Opens 9:30 AM ET"
            else:
                is_open = True
                status = "Unknown market"
                next_event = "Check specific market hours"
            
            output = f"=== MARKET HOURS ({market.upper()}) ===\\n"
            output += f"Current Status: {'🟢 OPEN' if is_open else '🔴 CLOSED'}\\n"
            output += f"Details: {status}\\n"
            output += f"Next Event: {next_event}\\n"
            output += f"Current Time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Market hours calculation failed: {str(e)}", isError=True)]
            )
    
    async def candle_time_info(self, args: dict) -> CallToolResult:
        """Get candle timing information"""
        timeframe = args.get("timeframe", "15m")
        timezone_str = args.get("timezone", "UTC")
        
        try:
            now = datetime.now(pytz.UTC)
            
            # Convert timeframe to minutes
            timeframe_minutes = {
                "1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440
            }
            
            if timeframe not in timeframe_minutes:
                return CallToolResult(
                    content=[ToolMessage(content=f"Unknown timeframe: {timeframe}", isError=True)]
                )
            
            minutes = timeframe_minutes[timeframe]
            
            # Calculate current candle start time
            if timeframe == "1d":
                # Daily candles start at midnight UTC
                candle_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                candle_end = candle_start + timedelta(days=1)
            else:
                # Calculate minutes since midnight
                minutes_since_midnight = now.hour * 60 + now.minute
                candle_number = minutes_since_midnight // minutes
                candle_start_minutes = candle_number * minutes
                
                candle_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=candle_start_minutes)
                candle_end = candle_start + timedelta(minutes=minutes)
            
            time_elapsed = now - candle_start
            time_remaining = candle_end - now
            progress_percent = (time_elapsed.total_seconds() / (minutes * 60)) * 100
            
            output = f"=== CANDLE TIMING ({timeframe.upper()}) ===\\n"
            output += f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n"
            output += f"Candle Start: {candle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n"
            output += f"Candle End: {candle_end.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n"
            output += f"Time Elapsed: {str(time_elapsed).split('.')[0]}\\n"
            output += f"Time Remaining: {str(time_remaining).split('.')[0]}\\n"
            output += f"Progress: {progress_percent:.1f}%\\n"
            output += f"Next Candle: {candle_end.strftime('%H:%M:%S UTC')}"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Candle time calculation failed: {str(e)}", isError=True)]
            )
    
    async def trading_session_info(self, args: dict) -> CallToolResult:
        """Get trading session information"""
        timezone_str = args.get("timezone", "UTC")
        
        try:
            now = datetime.now(pytz.UTC)
            
            # Define major trading sessions
            sessions = {
                "Sydney": {"start": 22, "end": 7, "tz": "Australia/Sydney"},
                "Tokyo": {"start": 0, "end": 9, "tz": "Asia/Tokyo"}, 
                "London": {"start": 8, "end": 17, "tz": "Europe/London"},
                "New York": {"start": 13, "end": 22, "tz": "America/New_York"}
            }
            
            active_sessions = []
            upcoming_sessions = []
            
            for session_name, info in sessions.items():
                start_hour = info["start"]
                end_hour = info["end"]
                
                # Handle sessions that cross midnight
                if start_hour > end_hour:
                    if now.hour >= start_hour or now.hour < end_hour:
                        active_sessions.append(session_name)
                else:
                    if start_hour <= now.hour < end_hour:
                        active_sessions.append(session_name)
            
            output = f"=== TRADING SESSIONS ===\\n"
            output += f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n\\n"
            
            if active_sessions:
                output += f"🟢 Active Sessions: {', '.join(active_sessions)}\\n"
            else:
                output += f"🔴 No Major Sessions Active\\n"
            
            output += f"\\n📊 Session Schedule (UTC):\\n"
            output += f"Sydney: 22:00 - 07:00\\n"
            output += f"Tokyo: 00:00 - 09:00\\n"  
            output += f"London: 08:00 - 17:00\\n"
            output += f"New York: 13:00 - 22:00\\n"
            
            # Market overlap periods
            output += f"\\n🔥 High Volume Overlaps:\\n"
            output += f"Tokyo + London: 08:00 - 09:00 UTC\\n"
            output += f"London + NY: 13:00 - 17:00 UTC"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Session info calculation failed: {str(e)}", isError=True)]
            )
    
    async def time_until(self, args: dict) -> CallToolResult:
        """Calculate time until target"""
        target_time_str = args.get("target_time")
        timezone_str = args.get("timezone", "UTC")
        
        try:
            now = datetime.now(pytz.UTC)
            
            # Try to parse target time
            try:
                target_time = datetime.fromisoformat(target_time_str.replace('Z', '+00:00'))
                if target_time.tzinfo is None:
                    target_time = target_time.replace(tzinfo=pytz.UTC)
            except:
                # Try alternative parsing
                try:
                    target_time = datetime.strptime(target_time_str, '%Y-%m-%d %H:%M:%S')
                    target_time = target_time.replace(tzinfo=pytz.UTC)
                except:
                    return CallToolResult(
                        content=[ToolMessage(content=f"Unable to parse target time: {target_time_str}", isError=True)]
                    )
            
            time_diff = target_time - now
            
            if time_diff.total_seconds() < 0:
                output = f"Target time has already passed\\n"
                output += f"Time since: {str(abs(time_diff)).split('.')[0]} ago"
            else:
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                output = f"=== TIME UNTIL TARGET ===\\n"
                output += f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n"
                output += f"Target Time: {target_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n"
                output += f"Time Remaining: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Time calculation failed: {str(e)}", isError=True)]
            )
    
    async def schedule_reminder(self, args: dict) -> CallToolResult:
        """Schedule trading activity reminder"""
        activity = args.get("activity")
        preferred_time = args.get("preferred_time", "auto")
        market_consideration = args.get("market_consideration", True)
        
        try:
            now = datetime.now(pytz.UTC)
            
            output = f"=== ACTIVITY SCHEDULING ===\\n"
            output += f"Activity: {activity}\\n"
            output += f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\\n\\n"
            
            if preferred_time == "auto":
                if market_consideration:
                    # Suggest optimal trading times
                    if "analysis" in activity.lower():
                        suggested_time = "Before market open or during low volatility periods"
                    elif "trade" in activity.lower():
                        suggested_time = "During high volume sessions (London/NY overlap: 13:00-17:00 UTC)"
                    elif "review" in activity.lower():
                        suggested_time = "After market close or during weekend"
                    else:
                        suggested_time = "During active trading hours"
                    
                    output += f"💡 Suggested Timing: {suggested_time}\\n"
                    output += f"🔥 High Volume Period: 13:00-17:00 UTC (London/NY overlap)\\n"
                    output += f"📊 Analysis Period: 22:00-08:00 UTC (Low volatility)\\n"
                else:
                    output += f"⏰ Schedule at your convenience\\n"
            else:
                output += f"Scheduled Time: {preferred_time}\\n"
            
            output += f"\\n📅 Market Considerations:\\n"
            output += f"Crypto: 24/7 trading available\\n"
            output += f"Forex: Closed weekends\\n"
            output += f"Stocks: Weekdays only"
            
            return CallToolResult(
                content=[ToolMessage(content=output)]
            )
        except Exception as e:
            return CallToolResult(
                content=[ToolMessage(content=f"Scheduling failed: {str(e)}", isError=True)]
            )

async def main():
    """Main entry point"""
    time_server = TimeServer()
    
    async with time_server.server.stdio_client() as streams:
        await time_server.server.request_loop(*streams)

if __name__ == "__main__":
    asyncio.run(main())
