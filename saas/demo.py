#!/usr/bin/env python3
"""
SaaS Platform Demo Script
=========================

Demonstrates the key features and revenue streams of the platform.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from app.core.database import create_tables
from app.schemas.strategy_schemas import StrategyCreate
from app.schemas.user_schemas import UserCreate
from app.services.analytics_service import AnalyticsService
from app.services.api_service import APIService
from app.services.payment_service import PaymentService
from app.services.strategy_marketplace import StrategyMarketplace
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService


async def demo_saas_platform():
    """Demonstrate SaaS platform capabilities"""
    print("🚀 CRYPTO TRADING BOT SAAS PLATFORM DEMO")
    print("=" * 60)

    # Initialize database
    await create_tables()

    # Initialize services
    user_service = UserService()
    subscription_service = SubscriptionService()
    payment_service = PaymentService()
    marketplace = StrategyMarketplace()
    api_service = APIService()
    analytics_service = AnalyticsService()

    # Initialize subscription tiers
    await subscription_service.initialize_default_tiers()

    print("✅ Platform initialized successfully!\n")

    # 1. USER REGISTRATION AND SUBSCRIPTION TIERS
    print("1️⃣ USER REGISTRATION & SUBSCRIPTION TIERS")
    print("-" * 40)

    # Create sample users
    users = []
    user_data = [
        {
            "email": "trader1@example.com",
            "username": "trader1",
            "password": "SecurePass123!",
            "full_name": "Professional Trader",
            "company": "Trading Corp"
        },
        {
            "email": "developer@example.com",
            "username": "dev_user",
            "password": "DevPass123!",
            "full_name": "API Developer",
            "company": "Tech Startup"
        },
        {
            "email": "institution@example.com",
            "username": "enterprise",
            "password": "EnterprisePass123!",
            "full_name": "Institution Manager",
            "company": "Big Bank Corp"
        }
    ]

    for user_info in user_data:
        user = await user_service.create_user(UserCreate(**user_info))
        users.append(user)
        print(f"✅ Created user: {user.username} ({user.subscription_tier} tier)")

    # Upgrade subscriptions
    await subscription_service.upgrade_subscription(users[0].id, "pro", "monthly")
    await subscription_service.upgrade_subscription(users[2].id, "enterprise", "yearly")
    print("✅ Upgraded subscriptions: Pro and Enterprise tiers\n")

    # 2. STRATEGY MARKETPLACE
    print("2️⃣ STRATEGY MARKETPLACE")
    print("-" * 40)

    # Create sample strategies
    strategy_data = [
        {
            "name": "RSI Mean Reversion",
            "description": "A profitable RSI-based mean reversion strategy for BTC/USDT",
            "short_description": "RSI mean reversion with 68% win rate",
            "strategy_code": """
def strategy_logic(data):
    rsi = calculate_rsi(data['close'], 14)
    if rsi < 30:
        return 'BUY'
    elif rsi > 70:
        return 'SELL'
    return 'HOLD'
            """,
            "is_public": True,
            "is_premium": True,
            "price": 99.99,
            "supported_exchanges": ["kraken", "binance"],
            "supported_pairs": ["BTC/USDT", "ETH/USDT"],
            "timeframes": ["1h", "4h"],
            "category": "mean_reversion",
            "risk_level": "medium",
            "tags": ["rsi", "bitcoin", "scalping"]
        },
        {
            "name": "Momentum Breakout Pro",
            "description": "Advanced momentum breakout strategy with dynamic position sizing",
            "short_description": "High-performance breakout strategy",
            "strategy_code": """
def strategy_logic(data):
    sma_20 = calculate_sma(data['close'], 20)
    sma_50 = calculate_sma(data['close'], 50)
    volume_avg = calculate_sma(data['volume'], 10)
    
    if data['close'][-1] > sma_20[-1] and data['volume'][-1] > volume_avg[-1] * 1.5:
        return 'BUY'
    elif data['close'][-1] < sma_50[-1]:
        return 'SELL'
    return 'HOLD'
            """,
            "is_public": True,
            "is_premium": True,
            "price": 199.99,
            "supported_exchanges": ["kraken", "binance", "coinbase"],
            "supported_pairs": ["BTC/USDT", "ETH/USDT", "ADA/USDT"],
            "timeframes": ["15m", "1h", "4h"],
            "category": "momentum",
            "risk_level": "high",
            "tags": ["momentum", "breakout", "volume"]
        }
    ]

    strategies = []
    for i, strat_data in enumerate(strategy_data):
        strategy = await marketplace.create_strategy(users[i].id, StrategyCreate(**strat_data))
        await marketplace.publish_strategy(strategy.id, users[i].id)
        await marketplace.approve_strategy(strategy.id, "Approved for marketplace")
        strategies.append(strategy)
        print(f"✅ Created strategy: {strategy.name} (${strategy.price})")

    # Simulate strategy purchases
    purchase, payment_secret = await marketplace.purchase_strategy(
        strategies[0].id, users[1].id, "stripe"
    )
    print(f"✅ Strategy purchase created: ${purchase.price_paid} (30% commission = ${purchase.commission_amount})")

    # Get marketplace stats
    stats = await marketplace.get_marketplace_stats()
    print(f"📊 Marketplace: {stats['published_strategies']} strategies, ${stats['total_revenue']} revenue\n")

    # 3. API MONETIZATION
    print("3️⃣ API MONETIZATION")
    print("-" * 40)

    # Create API keys for different tiers
    from app.schemas.api_schemas import APIKeyCreate

    api_keys = []
    for user in users:
        key, raw_key = await api_service.create_api_key(
            user.id,
            APIKeyCreate(
                name=f"{user.username}_api_key",
                description="Main API key for trading bot",
                scopes=["read", "write", "trade"]
            )
        )
        api_keys.append((key, raw_key))
        print(f"✅ Created API key for {user.username}: {raw_key[:20]}...")

    # Simulate API usage
    for i, (key, raw_key) in enumerate(api_keys):
        for _ in range(10):  # Simulate 10 requests
            await api_service.record_api_usage(
                key.id,
                "/api/v1/trading/execute",
                "POST",
                200,
                150,  # 150ms response time
                billable_units=1
            )

        # Check rate limits
        limits = await api_service.check_rate_limits(key.id)
        print(f"📊 {users[i].username} API usage: {limits['limits']['per_day']['used']}/{limits['limits']['per_day']['limit']} daily requests")

    print()

    # 4. WHITE-LABEL SOLUTIONS
    print("4️⃣ WHITE-LABEL SOLUTIONS")
    print("-" * 40)

    # Create white-label config for enterprise user
    white_label_config = await subscription_service.create_white_label_config(
        users[2].id,
        {
            "company_name": "Big Bank Trading Platform",
            "logo_url": "https://bigbank.com/logo.png",
            "primary_color": "#1f2937",
            "secondary_color": "#3b82f6",
            "custom_domain": "trading.bigbank.com",
            "enabled_features": [
                "custom_branding", "dedicated_support", "api_access",
                "advanced_analytics", "multi_exchange", "institutional_features"
            ],
            "monthly_fee": 15000.00
        }
    )
    print(f"✅ White-label solution: {white_label_config.company_name}")
    print(f"💰 Monthly fee: ${white_label_config.monthly_fee}/month\n")

    # 5. REVENUE ANALYTICS
    print("5️⃣ REVENUE ANALYTICS")
    print("-" * 40)

    # Generate some sample payments
    sample_payments = [
        {"user_id": users[0].id, "amount": 99.00, "type": "subscription"},
        {"user_id": users[1].id, "amount": 99.99, "type": "strategy_purchase"},
        {"user_id": users[2].id, "amount": 999.00, "type": "subscription"},
        {"user_id": users[2].id, "amount": 15000.00, "type": "white_label"}
    ]

    total_revenue = Decimal("0")
    for payment_data in sample_payments:
        # In a real scenario, these would go through Stripe
        total_revenue += Decimal(str(payment_data["amount"]))

    print(f"💰 Total Platform Revenue: ${total_revenue}")
    print(f"💰 Strategy Marketplace Commission (30%): ${Decimal('99.99') * Decimal('0.30')}")
    print(f"💰 Monthly Recurring Revenue: ${Decimal('99.00') + Decimal('999.00') + Decimal('15000.00')}")

    # Get subscription stats
    subscription_stats = await subscription_service.get_subscription_stats()
    print(f"📊 Active Subscriptions: {subscription_stats['total_active_subscriptions']}")
    print(f"📊 Estimated Monthly Revenue: ${subscription_stats['estimated_monthly_revenue']}")

    print("\n" + "=" * 60)
    print("🎉 SAAS PLATFORM DEMO COMPLETE!")
    print("=" * 60)

    print("\n🚀 REVENUE STREAMS SUMMARY:")
    print("1️⃣ Subscription Tiers: $99/month (Pro), $999/month (Enterprise)")
    print("2️⃣ Strategy Marketplace: 30% commission on all sales")
    print("3️⃣ API Usage: Rate-limited tiers with usage-based billing")
    print("4️⃣ White-Label Solutions: Starting at $10,000/month")
    print("5️⃣ Enterprise Features: Custom pricing and dedicated support")

    print("\n📈 SCALABILITY FEATURES:")
    print("• Multi-tenant architecture with subscription-based limits")
    print("• Automated billing and payment processing")
    print("• Comprehensive analytics and business intelligence")
    print("• Rate limiting and API monetization")
    print("• Revenue sharing for strategy creators")
    print("• Enterprise-grade security and compliance")

    print("\n🎯 TARGET MARKETS:")
    print("• Individual crypto traders (Free/Pro tiers)")
    print("• Trading firms and hedge funds (Enterprise tier)")
    print("• Fintech companies (API access and integrations)")
    print("• Financial institutions (White-label solutions)")
    print("• Strategy developers (Marketplace revenue sharing)")


if __name__ == "__main__":
    try:
        asyncio.run(demo_saas_platform())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
