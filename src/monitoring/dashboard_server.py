"""
Production Monitor Dashboard Server
==================================

FastAPI server providing real-time web dashboard for production monitoring.
Features WebSocket updates, RESTful API, and comprehensive monitoring interface.

Endpoints:
- GET /api/status - Current system status
- GET /api/metrics - Current metrics
- GET /api/metrics/history - Historical metrics
- GET /api/alerts - Recent alerts
- POST /api/control/emergency-stop - Emergency shutdown
- WS /ws - Real-time WebSocket updates
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from .production_monitor import ProductionMonitor, get_production_monitor, MetricThresholds, AlertConfig


logger = logging.getLogger(__name__)


# Pydantic models for API
class SystemStatusResponse(BaseModel):
    status: str
    message: str
    last_update: Optional[str]
    uptime_minutes: float
    metrics_summary: Dict[str, Any]


class MetricsResponse(BaseModel):
    timestamp: float
    trades_executed: int
    success_rate: float
    total_pnl: float
    daily_pnl: float
    memory_usage_mb: float
    api_errors: int
    websocket_status: str
    balance_manager_health: str


class AlertResponse(BaseModel):
    id: str
    metric: str
    message: str
    severity: str
    timestamp: float
    resolved: bool


class EmergencyStopRequest(BaseModel):
    reason: Optional[str] = "Manual dashboard trigger"
    confirm: bool = True


class DashboardServer:
    """Real-time dashboard server for production monitoring"""
    
    def __init__(self, monitor: ProductionMonitor, port: int = 8000):
        self.monitor = monitor
        self.port = port
        self.app = FastAPI(
            title="Crypto Trading Bot Production Monitor",
            description="Real-time monitoring dashboard for crypto trading bot",
            version="1.0.0"
        )
        
        # WebSocket connection manager
        self.websocket_connections: List[WebSocket] = []
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        
        # Register with monitor for updates
        self.monitor.register_dashboard_callback(self._handle_monitor_update)
        
        logger.info(f"Dashboard server initialized on port {port}")
    
    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True, 
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with basic info"""
            return {
                "name": "Crypto Trading Bot Production Monitor",
                "version": "1.0.0",
                "status": "running",
                "endpoints": [
                    "/api/status",
                    "/api/metrics", 
                    "/api/metrics/history",
                    "/api/alerts",
                    "/ws"
                ]
            }
        
        @self.app.get("/api/status", response_model=SystemStatusResponse)
        async def get_system_status():
            """Get overall system status"""
            status = self.monitor.get_system_status()
            return SystemStatusResponse(**status)
        
        @self.app.get("/api/metrics")
        async def get_current_metrics():
            """Get current metrics snapshot"""
            metrics = self.monitor.get_current_metrics()
            if not metrics:
                raise HTTPException(status_code=404, detail="No metrics available")
            
            return {
                "timestamp": metrics.timestamp,
                "trades_executed": metrics.trades_executed,
                "trades_successful": metrics.trades_successful,
                "trades_failed": metrics.trades_failed,
                "success_rate": metrics.success_rate,
                "total_pnl": metrics.total_pnl,
                "daily_pnl": metrics.daily_pnl,
                "nonce_failures": metrics.nonce_failures,
                "nonce_generation_rate": metrics.nonce_generation_rate,
                "websocket_reconnects": metrics.websocket_reconnects,
                "websocket_latency_ms": metrics.websocket_latency_ms,
                "api_errors": metrics.api_errors,
                "api_error_rate": metrics.api_error_rate,
                "memory_usage_mb": metrics.memory_usage_mb,
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "log_file_size_mb": metrics.log_file_size_mb,
                "log_rotation_count": metrics.log_rotation_count,
                "balance_manager_health": metrics.balance_manager_health,
                "balance_manager_response_time": metrics.balance_manager_response_time,
                "websocket_status": metrics.websocket_status,
                "websocket_connection_count": metrics.websocket_connection_count,
                "trade_execution_time_ms": metrics.trade_execution_time_ms,
                "balance_check_time_ms": metrics.balance_check_time_ms,
                "order_processing_time_ms": metrics.order_processing_time_ms
            }
        
        @self.app.get("/api/metrics/history")
        async def get_metrics_history(minutes: int = 60):
            """Get historical metrics"""
            history = self.monitor.get_metric_history(minutes)
            return [
                {
                    "timestamp": m.timestamp,
                    "trades_executed": m.trades_executed,
                    "success_rate": m.success_rate,
                    "total_pnl": m.total_pnl,
                    "daily_pnl": m.daily_pnl,
                    "memory_usage_mb": m.memory_usage_mb,
                    "api_errors": m.api_errors,
                    "websocket_status": m.websocket_status,
                    "balance_manager_health": m.balance_manager_health
                }
                for m in history
            ]
        
        @self.app.get("/api/alerts")
        async def get_alerts(minutes: int = 60):
            """Get recent alerts"""
            alerts = self.monitor.get_alert_history(minutes)
            return alerts
        
        @self.app.post("/api/control/emergency-stop")
        async def emergency_stop(request: EmergencyStopRequest, background_tasks: BackgroundTasks):
            """Trigger emergency shutdown"""
            if not request.confirm:
                raise HTTPException(status_code=400, detail="Emergency stop requires confirmation")
            
            logger.warning(f"Emergency stop requested via dashboard: {request.reason}")
            
            # Trigger shutdown in background
            background_tasks.add_task(self.monitor.trigger_emergency_shutdown, request.reason)
            
            return {
                "success": True,
                "message": "Emergency shutdown initiated",
                "reason": request.reason,
                "timestamp": time.time()
            }
        
        @self.app.get("/api/thresholds")
        async def get_thresholds():
            """Get current alert thresholds"""
            return {
                "memory_usage_mb": self.monitor.thresholds.memory_usage_mb,
                "log_file_size_mb": self.monitor.thresholds.log_file_size_mb,
                "nonce_generation_rate": self.monitor.thresholds.nonce_generation_rate,
                "websocket_reconnects_per_hour": self.monitor.thresholds.websocket_reconnects_per_hour,
                "api_error_rate_percent": self.monitor.thresholds.api_error_rate_percent,
                "trading_success_rate_percent": self.monitor.thresholds.trading_success_rate_percent,
                "daily_pnl_loss_limit": self.monitor.thresholds.daily_pnl_loss_limit,
                "balance_manager_response_time": self.monitor.thresholds.balance_manager_response_time,
                "websocket_latency_ms": self.monitor.thresholds.websocket_latency_ms,
                "trade_execution_time_ms": self.monitor.thresholds.trade_execution_time_ms
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                # Send initial data
                await self._send_websocket_update(websocket)
                
                # Keep connection alive
                while True:
                    try:
                        # Ping every 30 seconds
                        await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    except asyncio.TimeoutError:
                        # Send ping
                        await websocket.send_json({"type": "ping", "timestamp": time.time()})
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
    
    async def _handle_monitor_update(self, metrics, alerts):
        """Handle updates from production monitor"""
        # Broadcast to all WebSocket connections
        update_data = {
            "type": "metrics_update",
            "timestamp": time.time(),
            "metrics": {
                "trades_executed": metrics.trades_executed,
                "success_rate": metrics.success_rate,
                "total_pnl": metrics.total_pnl,
                "daily_pnl": metrics.daily_pnl,
                "memory_usage_mb": metrics.memory_usage_mb,
                "api_errors": metrics.api_errors,
                "websocket_status": metrics.websocket_status,
                "balance_manager_health": metrics.balance_manager_health,
                "websocket_latency_ms": metrics.websocket_latency_ms,
                "nonce_generation_rate": metrics.nonce_generation_rate
            },
            "alerts": alerts,
            "system_status": self.monitor.get_system_status()
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(update_data)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            if ws in self.websocket_connections:
                self.websocket_connections.remove(ws)
    
    async def _send_websocket_update(self, websocket: WebSocket):
        """Send current data to a specific WebSocket"""
        try:
            metrics = self.monitor.get_current_metrics()
            if metrics:
                update_data = {
                    "type": "initial_data",
                    "timestamp": time.time(),
                    "metrics": {
                        "trades_executed": metrics.trades_executed,
                        "success_rate": metrics.success_rate,
                        "total_pnl": metrics.total_pnl,
                        "daily_pnl": metrics.daily_pnl,
                        "memory_usage_mb": metrics.memory_usage_mb,
                        "api_errors": metrics.api_errors,
                        "websocket_status": metrics.websocket_status,
                        "balance_manager_health": metrics.balance_manager_health
                    },
                    "system_status": self.monitor.get_system_status(),
                    "alerts": self.monitor.get_alert_history(60)
                }
                await websocket.send_json(update_data)
        except Exception as e:
            logger.error(f"WebSocket initial data send error: {e}")
    
    async def start(self):
        """Start the dashboard server"""
        logger.info(f"Starting dashboard server on port {self.port}")
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


class DashboardHTML:
    """Generate HTML dashboard for standalone deployment"""
    
    @staticmethod
    def generate_dashboard_html() -> str:
        """Generate complete HTML dashboard with embedded CSS and JavaScript"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Trading Bot - Production Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f0f23;
            color: #e5e5e5;
            min-height: 100vh;
        }
        
        .header {
            background: #1a1a2e;
            padding: 1rem 2rem;
            border-bottom: 2px solid #16213e;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .title {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4CAF50;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-healthy { background: #4CAF50; }
        .status-warning { background: #FF9800; }
        .status-critical { background: #F44336; }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 1rem;
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .card {
            background: #1a1a2e;
            border: 1px solid #16213e;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .card-title {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 1rem;
            color: #4CAF50;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #888;
        }
        
        .metric-positive { color: #4CAF50; }
        .metric-negative { color: #F44336; }
        .metric-neutral { color: #e5e5e5; }
        
        .alerts-section {
            grid-column: 1 / -1;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .alert {
            background: #2a2a3e;
            border-left: 4px solid;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
        }
        
        .alert-info { border-color: #2196F3; }
        .alert-warning { border-color: #FF9800; }
        .alert-critical { border-color: #F44336; }
        
        .emergency-controls {
            grid-column: 1 / -1;
            text-align: center;
            padding: 2rem;
            background: #2a1a1a;
            border: 2px solid #F44336;
        }
        
        .emergency-btn {
            background: #F44336;
            color: white;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.1rem;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .emergency-btn:hover {
            background: #d32f2f;
        }
        
        .chart-container {
            height: 200px;
            background: #16213e;
            border-radius: 4px;
            padding: 1rem;
            position: relative;
        }
        
        .connection-status {
            position: fixed;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: bold;
        }
        
        .connected {
            background: #4CAF50;
            color: white;
        }
        
        .disconnected {
            background: #F44336;
            color: white;
        }
        
        @media (max-width: 768px) {
            .dashboard {
                grid-template-columns: 1fr;
                padding: 1rem;
            }
            
            .header {
                padding: 1rem;
                flex-direction: column;
                gap: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>
    
    <div class="header">
        <div class="title">Crypto Trading Bot - Production Monitor</div>
        <div class="status-indicator">
            <div class="status-dot status-healthy" id="statusDot"></div>
            <span id="systemStatus">Initializing...</span>
        </div>
    </div>
    
    <div class="dashboard">
        <!-- Trading Metrics -->
        <div class="card">
            <div class="card-title">Trading Performance</div>
            <div class="metric-value metric-neutral" id="tradesExecuted">-</div>
            <div class="metric-label">Trades Executed</div>
            <div class="metric-value metric-positive" id="successRate">-</div>
            <div class="metric-label">Success Rate</div>
        </div>
        
        <div class="card">
            <div class="card-title">Profit & Loss</div>
            <div class="metric-value" id="totalPnl">-</div>
            <div class="metric-label">Total P&L</div>
            <div class="metric-value" id="dailyPnl">-</div>
            <div class="metric-label">Daily P&L</div>
        </div>
        
        <div class="card">
            <div class="card-title">System Resources</div>
            <div class="metric-value metric-neutral" id="memoryUsage">-</div>
            <div class="metric-label">Memory Usage (MB)</div>
            <div class="metric-value metric-neutral" id="apiErrors">-</div>
            <div class="metric-label">API Errors</div>
        </div>
        
        <!-- Component Health -->
        <div class="card">
            <div class="card-title">WebSocket Status</div>
            <div class="metric-value" id="websocketStatus">-</div>
            <div class="metric-label">Connection Status</div>
            <div class="metric-value metric-neutral" id="websocketLatency">-</div>
            <div class="metric-label">Latency (ms)</div>
        </div>
        
        <div class="card">
            <div class="card-title">Balance Manager</div>
            <div class="metric-value" id="balanceManagerHealth">-</div>
            <div class="metric-label">Health Status</div>
            <div class="metric-value metric-neutral" id="balanceResponseTime">-</div>
            <div class="metric-label">Response Time (ms)</div>
        </div>
        
        <div class="card">
            <div class="card-title">Nonce System</div>
            <div class="metric-value metric-neutral" id="nonceRate">-</div>
            <div class="metric-label">Generation Rate (/sec)</div>
            <div class="metric-value metric-neutral" id="nonceFailures">-</div>
            <div class="metric-label">Failures</div>
        </div>
        
        <!-- Performance Chart -->
        <div class="card" style="grid-column: 1 / -1;">
            <div class="card-title">Performance Trends</div>
            <div class="chart-container" id="performanceChart">
                <div style="text-align: center; padding-top: 80px; color: #888;">
                    Performance chart will appear here
                </div>
            </div>
        </div>
        
        <!-- Alerts Section -->
        <div class="card alerts-section">
            <div class="card-title">Recent Alerts</div>
            <div id="alertsList">
                <div style="text-align: center; color: #888; padding: 2rem;">
                    No alerts
                </div>
            </div>
        </div>
        
        <!-- Emergency Controls -->
        <div class="emergency-controls">
            <h3 style="margin-bottom: 1rem; color: #F44336;">Emergency Controls</h3>
            <button class="emergency-btn" onclick="confirmEmergencyStop()">
                EMERGENCY STOP
            </button>
            <p style="margin-top: 1rem; color: #888;">
                This will immediately halt all trading and cancel open orders
            </p>
        </div>
    </div>
    
    <script>
        let websocket = null;
        let reconnectInterval = null;
        
        // WebSocket connection management
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function() {
                console.log('WebSocket connected');
                updateConnectionStatus(true);
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            websocket.onclose = function() {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                scheduleReconnect();
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
        }
        
        function scheduleReconnect() {
            if (!reconnectInterval) {
                reconnectInterval = setInterval(() => {
                    console.log('Attempting to reconnect...');
                    connectWebSocket();
                }, 5000);
            }
        }
        
        function handleWebSocketMessage(data) {
            if (data.type === 'metrics_update' || data.type === 'initial_data') {
                updateMetrics(data.metrics);
                updateSystemStatus(data.system_status);
                updateAlerts(data.alerts);
            }
        }
        
        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connectionStatus');
            if (connected) {
                statusEl.textContent = 'Connected';
                statusEl.className = 'connection-status connected';
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'connection-status disconnected';
            }
        }
        
        function updateMetrics(metrics) {
            // Trading metrics
            document.getElementById('tradesExecuted').textContent = metrics.trades_executed || 0;
            
            const successRate = metrics.success_rate || 0;
            const successRateEl = document.getElementById('successRate');
            successRateEl.textContent = successRate.toFixed(1) + '%';
            successRateEl.className = 'metric-value ' + (successRate >= 85 ? 'metric-positive' : 'metric-negative');
            
            // P&L metrics
            const totalPnl = metrics.total_pnl || 0;
            const totalPnlEl = document.getElementById('totalPnl');
            totalPnlEl.textContent = '$' + totalPnl.toFixed(2);
            totalPnlEl.className = 'metric-value ' + (totalPnl >= 0 ? 'metric-positive' : 'metric-negative');
            
            const dailyPnl = metrics.daily_pnl || 0;
            const dailyPnlEl = document.getElementById('dailyPnl');
            dailyPnlEl.textContent = '$' + dailyPnl.toFixed(2);
            dailyPnlEl.className = 'metric-value ' + (dailyPnl >= 0 ? 'metric-positive' : 'metric-negative');
            
            // System metrics
            const memoryUsage = metrics.memory_usage_mb || 0;
            const memoryEl = document.getElementById('memoryUsage');
            memoryEl.textContent = memoryUsage.toFixed(1);
            memoryEl.className = 'metric-value ' + (memoryUsage > 500 ? 'metric-negative' : 'metric-neutral');
            
            document.getElementById('apiErrors').textContent = metrics.api_errors || 0;
            
            // Component health
            const wsStatus = metrics.websocket_status || 'unknown';
            const wsStatusEl = document.getElementById('websocketStatus');
            wsStatusEl.textContent = wsStatus;
            wsStatusEl.className = 'metric-value ' + (wsStatus === 'connected' ? 'metric-positive' : 'metric-negative');
            
            document.getElementById('websocketLatency').textContent = (metrics.websocket_latency_ms || 0).toFixed(0);
            
            const bmHealth = metrics.balance_manager_health || 'unknown';
            const bmHealthEl = document.getElementById('balanceManagerHealth');
            bmHealthEl.textContent = bmHealth;
            bmHealthEl.className = 'metric-value ' + (bmHealth === 'healthy' ? 'metric-positive' : 'metric-negative');
            
            document.getElementById('balanceResponseTime').textContent = (metrics.balance_manager_response_time || 0).toFixed(0);
            document.getElementById('nonceRate').textContent = (metrics.nonce_generation_rate || 0).toFixed(0);
            document.getElementById('nonceFailures').textContent = metrics.nonce_failures || 0;
        }
        
        function updateSystemStatus(status) {
            const statusEl = document.getElementById('systemStatus');
            const dotEl = document.getElementById('statusDot');
            
            statusEl.textContent = status.status;
            
            // Update dot color based on status
            dotEl.className = 'status-dot';
            if (status.status === 'healthy') {
                dotEl.classList.add('status-healthy');
            } else if (status.status === 'warning') {
                dotEl.classList.add('status-warning');
            } else {
                dotEl.classList.add('status-critical');
            }
        }
        
        function updateAlerts(alerts) {
            const alertsList = document.getElementById('alertsList');
            
            if (!alerts || alerts.length === 0) {
                alertsList.innerHTML = '<div style="text-align: center; color: #888; padding: 2rem;">No alerts</div>';
                return;
            }
            
            const alertsHtml = alerts.map(alert => {
                const timestamp = new Date(alert.timestamp * 1000).toLocaleTimeString();
                return `
                    <div class="alert alert-${alert.severity}">
                        <strong>${alert.severity.toUpperCase()}</strong> - ${alert.message}
                        <div style="font-size: 0.8rem; color: #888; margin-top: 0.5rem;">${timestamp}</div>
                    </div>
                `;
            }).join('');
            
            alertsList.innerHTML = alertsHtml;
        }
        
        function confirmEmergencyStop() {
            if (confirm('Are you sure you want to trigger an emergency stop? This will halt all trading immediately.')) {
                triggerEmergencyStop();
            }
        }
        
        async function triggerEmergencyStop() {
            try {
                const response = await fetch('/api/control/emergency-stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        reason: 'Dashboard emergency stop',
                        confirm: true
                    })
                });
                
                if (response.ok) {
                    alert('Emergency stop initiated successfully');
                } else {
                    alert('Emergency stop failed');
                }
            } catch (error) {
                console.error('Emergency stop error:', error);
                alert('Emergency stop request failed');
            }
        }
        
        // Initialize connection
        connectWebSocket();
        
        // Refresh data every 30 seconds as fallback
        setInterval(async () => {
            if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                try {
                    const response = await fetch('/api/metrics');
                    if (response.ok) {
                        const metrics = await response.json();
                        updateMetrics(metrics);
                    }
                } catch (error) {
                    console.error('Fallback refresh error:', error);
                }
            }
        }, 30000);
    </script>
</body>
</html>
        """


# Standalone server for testing
async def start_dashboard_server(monitor: ProductionMonitor, port: int = 8000):
    """Start the dashboard server"""
    server = DashboardServer(monitor, port)
    await server.start()


if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    
    async def main():
        # Initialize monitor
        project_root = Path(__file__).parent.parent.parent
        monitor = get_production_monitor(project_root)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Start dashboard server
        server = DashboardServer(monitor, 8001)
        await server.start()
    
    asyncio.run(main())