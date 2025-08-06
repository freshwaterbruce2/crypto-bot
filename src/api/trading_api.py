"""
FastAPI-based trading API with subscription management.
Provides RESTful endpoints for bot control, monitoring, and trading operations.
"""
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .revenue_model import SubscriptionManager, SubscriptionTier, User


# API Models
class TradingSignal(BaseModel):
    """Trading signal model."""
    pair: str
    action: str = Field(..., regex="^(buy|sell|hold)$")
    confidence: float = Field(..., ge=0, le=1)
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class OrderRequest(BaseModel):
    """Order request model."""
    pair: str
    type: str = Field(..., regex="^(market|limit|stop)$")
    side: str = Field(..., regex="^(buy|sell)$")
    volume: float = Field(..., gt=0)
    price: Optional[float] = None
    stop_price: Optional[float] = None


class BalanceResponse(BaseModel):
    """Balance response model."""
    currency: str
    available: float
    total: float
    reserved: float


class PerformanceMetrics(BaseModel):
    """Performance metrics response."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    roi: float


class BacktestRequest(BaseModel):
    """Backtest request model."""
    strategy: str
    pair: str
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    parameters: Optional[dict] = None


class StrategyConfig(BaseModel):
    """Strategy configuration model."""
    name: str
    enabled: bool = True
    parameters: dict
    pairs: list[str]
    risk_limit: float = 0.02


# Initialize FastAPI app
app = FastAPI(
    title="Crypto Trading Bot API",
    description="Professional cryptocurrency trading bot with subscription management",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
security = HTTPBearer()
subscription_manager = SubscriptionManager(secret_key="your-secret-key-here")


# Dependency for authentication
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> User:
    """Get current authenticated user."""
    user_info = subscription_manager.verify_api_key(credentials)
    # In production, fetch from database
    return User(
        id=user_info["user_id"],
        email=f"{user_info['user_id']}@example.com",
        subscription_tier=user_info["tier"],
    )


# Public endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Crypto Trading Bot API",
        "version": "2.0.0",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "api": "operational",
            "trading_engine": "operational",
            "websocket": "operational",
            "database": "operational",
        },
    }


@app.get("/api/subscription/tiers")
async def get_subscription_tiers():
    """Get available subscription tiers."""
    from .revenue_model import SUBSCRIPTION_TIERS
    return SUBSCRIPTION_TIERS


# Authenticated endpoints
@app.get("/api/account/info")
async def get_account_info(user: User = Depends(get_current_user)):
    """Get account information."""
    features = subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]
    return {
        "user_id": user.id,
        "email": user.email,
        "subscription": {
            "tier": user.subscription_tier,
            "features": features,
            "api_calls_remaining": features.max_api_calls_per_month - user.api_calls_this_month,
        },
    }


@app.get("/api/balance", response_model=list[BalanceResponse])
async def get_balances(user: User = Depends(get_current_user)):
    """Get current account balances."""
    # Check rate limit
    if not subscription_manager.check_rate_limit(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded",
        )

    # In production, fetch from exchange
    return [
        BalanceResponse(
            currency="USD",
            available=10000.0,
            total=10500.0,
            reserved=500.0,
        ),
        BalanceResponse(
            currency="BTC",
            available=0.5,
            total=0.5,
            reserved=0.0,
        ),
    ]


@app.post("/api/orders")
async def create_order(
    order: OrderRequest,
    user: User = Depends(get_current_user),
):
    """Create a new trading order."""
    # Check subscription features
    subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]

    # Validate trading pair limit
    # In production, check against user's active pairs

    # Execute order
    return {
        "order_id": f"ORD-{datetime.utcnow().timestamp()}",
        "status": "pending",
        "pair": order.pair,
        "type": order.type,
        "side": order.side,
        "volume": order.volume,
        "price": order.price,
    }


@app.get("/api/orders")
async def get_orders(
    status: Optional[str] = None,
    pair: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
):
    """Get trading orders."""
    # In production, fetch from database with filters
    return {
        "orders": [],
        "total": 0,
    }


@app.get("/api/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period: str = "30d",
    user: User = Depends(get_current_user),
):
    """Get trading performance metrics."""
    # In production, calculate from trade history
    return PerformanceMetrics(
        total_trades=150,
        winning_trades=90,
        losing_trades=60,
        win_rate=0.6,
        total_pnl=2500.0,
        sharpe_ratio=1.5,
        max_drawdown=0.15,
        roi=0.25,
    )


@app.post("/api/backtest")
async def run_backtest(
    request: BacktestRequest,
    user: User = Depends(get_current_user),
):
    """Run strategy backtest."""
    # Check if backtesting is enabled for user's tier
    features = subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]
    if not features.backtesting_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backtesting not available in your subscription tier",
        )

    # In production, run actual backtest
    return {
        "backtest_id": f"BT-{datetime.utcnow().timestamp()}",
        "status": "running",
        "estimated_completion": "5 minutes",
    }


@app.get("/api/strategies")
async def get_strategies(user: User = Depends(get_current_user)):
    """Get available trading strategies."""
    subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]

    # Basic strategies available to all
    strategies = [
        {
            "id": "scalping_v1",
            "name": "Basic Scalping",
            "description": "High-frequency scalping strategy",
            "min_tier": "free",
        },
    ]

    # Pro strategies
    if user.subscription_tier in [SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE]:
        strategies.extend([
            {
                "id": "ai_predictor",
                "name": "AI Price Predictor",
                "description": "Machine learning-based price prediction",
                "min_tier": "pro",
            },
            {
                "id": "arbitrage_scanner",
                "name": "Arbitrage Scanner",
                "description": "Cross-exchange arbitrage detection",
                "min_tier": "pro",
            },
        ])

    return strategies


@app.post("/api/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    config: StrategyConfig,
    user: User = Depends(get_current_user),
):
    """Activate a trading strategy."""
    # Validate strategy limits
    subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]

    # In production, activate strategy
    return {
        "strategy_id": strategy_id,
        "status": "active",
        "config": config,
    }


@app.get("/api/signals/live")
async def get_live_signals(
    pair: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Get live trading signals (WebSocket endpoint in production)."""
    # Check if real-time alerts are enabled
    features = subscription_manager.SUBSCRIPTION_TIERS[user.subscription_tier]
    if not features.realtime_alerts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Real-time alerts not available in your subscription tier",
        )

    return {
        "signals": [
            TradingSignal(
                pair="BTC/USD",
                action="buy",
                confidence=0.85,
                price=50000.0,
            ),
        ],
    }


@app.post("/api/webhooks")
async def create_webhook(
    url: str,
    events: list[str],
    user: User = Depends(get_current_user),
):
    """Create webhook for automated notifications."""
    # Enterprise feature
    if user.subscription_tier != SubscriptionTier.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhooks are only available for Enterprise users",
        )

    return {
        "webhook_id": f"WH-{datetime.utcnow().timestamp()}",
        "url": url,
        "events": events,
        "status": "active",
    }


# Admin endpoints (for internal use)
@app.get("/api/admin/metrics")
async def get_revenue_metrics(
    admin_key: str,
):
    """Get revenue metrics (admin only)."""
    if admin_key != "your-admin-key":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # In production, calculate from database
    return {
        "total_users": 1500,
        "paying_users": 300,
        "mrr": 25000.0,
        "arr": 300000.0,
        "churn_rate": 0.05,
        "ltv": 1500.0,
    }


def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server."""
    uvicorn.run(app, host=host, port=port)
