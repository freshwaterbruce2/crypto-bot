"""
Strategy Marketplace Service
===========================

Service layer for trading strategy marketplace, including buying, selling,
revenue sharing, and strategy management.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.database import get_db_session
from ..models.strategy_models import Strategy, StrategyBacktest, StrategyPurchase, StrategyReview
from ..schemas.strategy_schemas import StrategyCreate, StrategyReviewCreate

logger = logging.getLogger(__name__)
settings = get_settings()


class StrategyMarketplace:
    """Strategy marketplace service"""

    def __init__(self):
        self.settings = get_settings()
        self.commission_rate = Decimal(str(self.settings.MARKETPLACE_COMMISSION))

    async def create_strategy(
        self,
        owner_id: int,
        strategy_data: StrategyCreate
    ) -> Strategy:
        """Create a new trading strategy"""
        async with get_db_session() as session:
            # Verify user has permission to create strategies
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()

            limits_check = await subscription_service.check_subscription_limits(
                owner_id, "strategies", 1
            )

            if not limits_check["allowed"]:
                raise ValueError(f"Strategy creation limit reached: {limits_check['reason']}")

            # Validate strategy code (basic validation)
            if not self._validate_strategy_code(strategy_data.strategy_code):
                raise ValueError("Invalid strategy code format")

            strategy = Strategy(
                owner_id=owner_id,
                name=strategy_data.name,
                description=strategy_data.description,
                short_description=strategy_data.short_description,
                strategy_code=strategy_data.strategy_code,
                parameters=strategy_data.parameters or {},
                default_config=strategy_data.default_config or {},
                is_public=strategy_data.is_public,
                is_premium=strategy_data.is_premium,
                price=Decimal(str(strategy_data.price)) if strategy_data.price else Decimal("0"),
                min_balance=Decimal(str(strategy_data.min_balance)) if strategy_data.min_balance else Decimal("0"),
                supported_exchanges=strategy_data.supported_exchanges or [],
                supported_pairs=strategy_data.supported_pairs or [],
                timeframes=strategy_data.timeframes or [],
                tags=strategy_data.tags or [],
                category=strategy_data.category,
                risk_level=strategy_data.risk_level or "medium",
                status="draft"
            )

            session.add(strategy)
            await session.flush()

            # Record strategy creation in usage
            await subscription_service.record_usage(
                owner_id, "strategies", 1,
                {"strategy_id": strategy.id, "strategy_name": strategy.name}
            )

            await session.commit()
            return strategy

    async def publish_strategy(self, strategy_id: int, owner_id: int) -> Strategy:
        """Publish strategy to marketplace"""
        async with get_db_session() as session:
            strategy = await session.get(Strategy, strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            if strategy.owner_id != owner_id:
                raise ValueError("You can only publish your own strategies")

            if strategy.status != "draft":
                raise ValueError("Only draft strategies can be published")

            # Validate strategy is complete
            if not all([strategy.name, strategy.description, strategy.strategy_code]):
                raise ValueError("Strategy must have name, description, and code")

            if strategy.is_premium and not strategy.price:
                raise ValueError("Premium strategies must have a price")

            # Run basic validation/testing
            validation_result = await self._validate_strategy_for_publication(strategy)
            if not validation_result["valid"]:
                raise ValueError(f"Strategy validation failed: {validation_result['reason']}")

            strategy.status = "pending"
            strategy.published_at = datetime.utcnow()
            strategy.updated_at = datetime.utcnow()

            await session.commit()
            return strategy

    async def approve_strategy(self, strategy_id: int, admin_notes: str = None) -> Strategy:
        """Approve strategy for marketplace (admin only)"""
        async with get_db_session() as session:
            strategy = await session.get(Strategy, strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            strategy.status = "approved"
            strategy.approval_notes = admin_notes
            strategy.updated_at = datetime.utcnow()

            # Notify owner of approval
            from .user_service import UserService
            user_service = UserService()
            await user_service.create_notification(
                strategy.owner_id,
                "Strategy Approved!",
                f"Your strategy '{strategy.name}' has been approved and is now live in the marketplace.",
                "success"
            )

            await session.commit()
            return strategy

    async def get_marketplace_strategies(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str = None,
        search: str = None,
        min_price: float = None,
        max_price: float = None,
        risk_level: str = None,
        sort_by: str = "popularity"
    ) -> list[Strategy]:
        """Get strategies from marketplace with filtering"""
        async with get_db_session() as session:
            stmt = select(Strategy).options(
                selectinload(Strategy.owner)
            ).where(
                and_(
                    Strategy.status == "approved",
                    Strategy.is_public
                )
            )

            # Apply filters
            if category:
                stmt = stmt.where(Strategy.category == category)

            if search:
                search_term = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        Strategy.name.ilike(search_term),
                        Strategy.description.ilike(search_term),
                        Strategy.tags.contains([search])
                    )
                )

            if min_price is not None:
                stmt = stmt.where(Strategy.price >= Decimal(str(min_price)))

            if max_price is not None:
                stmt = stmt.where(Strategy.price <= Decimal(str(max_price)))

            if risk_level:
                stmt = stmt.where(Strategy.risk_level == risk_level)

            # Apply sorting
            if sort_by == "popularity":
                stmt = stmt.order_by(desc(Strategy.downloads + Strategy.purchases))
            elif sort_by == "rating":
                stmt = stmt.order_by(desc(Strategy.rating))
            elif sort_by == "newest":
                stmt = stmt.order_by(desc(Strategy.published_at))
            elif sort_by == "price_low":
                stmt = stmt.order_by(Strategy.price)
            elif sort_by == "price_high":
                stmt = stmt.order_by(desc(Strategy.price))

            stmt = stmt.offset(skip).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_strategy_details(self, strategy_id: int, user_id: int = None) -> dict[str, Any]:
        """Get detailed strategy information"""
        async with get_db_session() as session:
            strategy = await session.get(
                Strategy,
                strategy_id,
                options=[
                    selectinload(Strategy.owner),
                    selectinload(Strategy.reviews).selectinload(StrategyReview.reviewer),
                    selectinload(Strategy.backtests)
                ]
            )

            if not strategy:
                raise ValueError("Strategy not found")

            if strategy.status != "approved" and strategy.owner_id != user_id:
                raise ValueError("Strategy not available")

            # Check if user owns this strategy
            user_owns = strategy.owner_id == user_id if user_id else False

            # Check if user has purchased this strategy
            user_purchased = False
            if user_id and not user_owns:
                purchase = await session.scalar(
                    select(StrategyPurchase).where(
                        and_(
                            StrategyPurchase.strategy_id == strategy_id,
                            StrategyPurchase.buyer_id == user_id,
                            StrategyPurchase.status == "completed"
                        )
                    )
                )
                user_purchased = bool(purchase)

            # Get recent reviews
            recent_reviews = strategy.reviews[:5] if strategy.reviews else []

            # Get performance data from backtests
            best_backtest = None
            if strategy.backtests:
                best_backtest = max(
                    strategy.backtests,
                    key=lambda bt: bt.total_return,
                    default=None
                )

            return {
                "strategy": strategy.to_dict(include_code=user_owns or user_purchased),
                "user_owns": user_owns,
                "user_purchased": user_purchased,
                "recent_reviews": [
                    {
                        "id": review.id,
                        "rating": review.rating,
                        "title": review.title,
                        "content": review.content,
                        "reviewer": review.reviewer.username if review.reviewer else "Anonymous",
                        "created_at": review.created_at.isoformat() if review.created_at else None
                    }
                    for review in recent_reviews
                ],
                "performance": {
                    "best_backtest": {
                        "total_return": float(best_backtest.total_return),
                        "max_drawdown": float(best_backtest.max_drawdown),
                        "win_rate": float(best_backtest.win_rate),
                        "total_trades": best_backtest.total_trades,
                        "period": f"{best_backtest.start_date.date()} to {best_backtest.end_date.date()}"
                    } if best_backtest else None
                }
            }

    async def purchase_strategy(
        self,
        strategy_id: int,
        buyer_id: int,
        payment_method: str = "stripe"
    ) -> tuple[StrategyPurchase, str]:
        """Purchase a strategy from the marketplace"""
        async with get_db_session() as session:
            strategy = await session.get(Strategy, strategy_id, options=[selectinload(Strategy.owner)])
            if not strategy:
                raise ValueError("Strategy not found")

            if strategy.status != "approved":
                raise ValueError("Strategy is not available for purchase")

            if strategy.owner_id == buyer_id:
                raise ValueError("You cannot purchase your own strategy")

            # Check if already purchased
            existing_purchase = await session.scalar(
                select(StrategyPurchase).where(
                    and_(
                        StrategyPurchase.strategy_id == strategy_id,
                        StrategyPurchase.buyer_id == buyer_id,
                        StrategyPurchase.status == "completed"
                    )
                )
            )

            if existing_purchase:
                raise ValueError("You have already purchased this strategy")

            if strategy.is_free:
                # Free strategy - create purchase record directly
                purchase = StrategyPurchase(
                    strategy_id=strategy_id,
                    buyer_id=buyer_id,
                    price_paid=Decimal("0"),
                    commission_rate=Decimal("0"),
                    commission_amount=Decimal("0"),
                    payment_method="free",
                    status="completed"
                )

                session.add(purchase)

                # Update strategy stats
                strategy.downloads += 1
                strategy.updated_at = datetime.utcnow()

                await session.commit()
                return purchase, None

            else:
                # Premium strategy - create payment
                commission_amount = strategy.price * self.commission_rate

                purchase = StrategyPurchase(
                    strategy_id=strategy_id,
                    buyer_id=buyer_id,
                    price_paid=strategy.price,
                    commission_rate=self.commission_rate,
                    commission_amount=commission_amount,
                    payment_method=payment_method,
                    status="pending"
                )

                session.add(purchase)
                await session.flush()

                # Create payment intent
                from .payment_service import PaymentService
                payment_service = PaymentService()

                payment_intent = await payment_service.create_payment_intent(
                    user_id=buyer_id,
                    amount=float(strategy.price),
                    payment_type="strategy_purchase",
                    reference_id=str(strategy_id),
                    metadata={
                        "strategy_name": strategy.name,
                        "seller_id": str(strategy.owner_id),
                        "purchase_id": str(purchase.id)
                    }
                )

                purchase.transaction_id = payment_intent["stripe_payment_intent_id"]

                await session.commit()
                return purchase, payment_intent["client_secret"]

    async def complete_strategy_purchase(self, purchase_id: int, payment_id: int) -> StrategyPurchase:
        """Complete strategy purchase after payment confirmation"""
        async with get_db_session() as session:
            purchase = await session.get(StrategyPurchase, purchase_id)
            if not purchase:
                raise ValueError("Purchase not found")

            purchase.status = "completed"

            # Update strategy stats
            strategy = await session.get(Strategy, purchase.strategy_id)
            if strategy:
                strategy.purchases += 1
                strategy.total_revenue += purchase.price_paid
                strategy.updated_at = datetime.utcnow()

            # Create payout record for strategy owner
            # This would be handled by a separate payout service

            await session.commit()
            return purchase

    async def create_review(
        self,
        strategy_id: int,
        reviewer_id: int,
        review_data: StrategyReviewCreate
    ) -> StrategyReview:
        """Create a strategy review"""
        async with get_db_session() as session:
            # Verify user has purchased the strategy
            purchase = await session.scalar(
                select(StrategyPurchase).where(
                    and_(
                        StrategyPurchase.strategy_id == strategy_id,
                        StrategyPurchase.buyer_id == reviewer_id,
                        StrategyPurchase.status == "completed"
                    )
                )
            )

            if not purchase:
                raise ValueError("You must purchase the strategy before reviewing it")

            # Check if user already reviewed
            existing_review = await session.scalar(
                select(StrategyReview).where(
                    and_(
                        StrategyReview.strategy_id == strategy_id,
                        StrategyReview.reviewer_id == reviewer_id
                    )
                )
            )

            if existing_review:
                raise ValueError("You have already reviewed this strategy")

            review = StrategyReview(
                strategy_id=strategy_id,
                reviewer_id=reviewer_id,
                rating=review_data.rating,
                title=review_data.title,
                content=review_data.content,
                actual_return=Decimal(str(review_data.actual_return)) if review_data.actual_return else None,
                usage_period_days=review_data.usage_period_days,
                is_verified=True  # Verified because they purchased it
            )

            session.add(review)
            await session.flush()

            # Update strategy rating
            await self._update_strategy_rating(strategy_id, session)

            await session.commit()
            return review

    async def run_backtest(
        self,
        strategy_id: int,
        user_id: int,
        backtest_params: dict[str, Any]
    ) -> StrategyBacktest:
        """Run backtest for a strategy"""
        async with get_db_session() as session:
            strategy = await session.get(Strategy, strategy_id)
            if not strategy:
                raise ValueError("Strategy not found")

            # Check if user can access this strategy
            can_access = (
                strategy.owner_id == user_id or
                strategy.status == "approved" or
                await self._user_purchased_strategy(strategy_id, user_id)
            )

            if not can_access:
                raise ValueError("Access denied to this strategy")

            # Create backtest record
            backtest = StrategyBacktest(
                strategy_id=strategy_id,
                user_id=user_id,
                start_date=datetime.fromisoformat(backtest_params["start_date"]),
                end_date=datetime.fromisoformat(backtest_params["end_date"]),
                initial_balance=Decimal(str(backtest_params["initial_balance"])),
                trading_pairs=backtest_params.get("trading_pairs", []),
                status="running"
            )

            session.add(backtest)
            await session.flush()

            # Run backtest (this would be async in production)
            try:
                results = await self._run_backtest_simulation(strategy, backtest_params)

                # Update backtest with results
                backtest.final_balance = Decimal(str(results["final_balance"]))
                backtest.total_return = Decimal(str(results["total_return"]))
                backtest.max_drawdown = Decimal(str(results["max_drawdown"]))
                backtest.win_rate = Decimal(str(results["win_rate"]))
                backtest.total_trades = results["total_trades"]
                backtest.winning_trades = results["winning_trades"]
                backtest.losing_trades = results["losing_trades"]
                backtest.sharpe_ratio = Decimal(str(results.get("sharpe_ratio", 0)))
                backtest.trade_history = results.get("trade_history", [])
                backtest.equity_curve = results.get("equity_curve", [])
                backtest.status = "completed"
                backtest.completed_at = datetime.utcnow()

            except Exception as e:
                backtest.status = "failed"
                backtest.error_message = str(e)
                logger.error(f"Backtest failed for strategy {strategy_id}: {e}")

            await session.commit()
            return backtest

    async def get_user_strategies(self, user_id: int) -> list[Strategy]:
        """Get strategies owned by user"""
        async with get_db_session() as session:
            stmt = select(Strategy).where(Strategy.owner_id == user_id).order_by(desc(Strategy.created_at))
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_user_purchases(self, user_id: int) -> list[StrategyPurchase]:
        """Get strategies purchased by user"""
        async with get_db_session() as session:
            stmt = select(StrategyPurchase).options(
                selectinload(StrategyPurchase.strategy).selectinload(Strategy.owner)
            ).where(
                and_(
                    StrategyPurchase.buyer_id == user_id,
                    StrategyPurchase.status == "completed"
                )
            ).order_by(desc(StrategyPurchase.created_at))

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_marketplace_stats(self) -> dict[str, Any]:
        """Get marketplace statistics"""
        async with get_db_session() as session:
            # Strategy counts
            total_strategies = await session.scalar(select(func.count(Strategy.id)))
            published_strategies = await session.scalar(
                select(func.count(Strategy.id)).where(Strategy.status == "approved")
            )

            # Purchase stats
            total_purchases = await session.scalar(select(func.count(StrategyPurchase.id)))
            total_revenue = await session.scalar(
                select(func.sum(StrategyPurchase.price_paid)).where(
                    StrategyPurchase.status == "completed"
                )
            ) or Decimal("0")

            # Top categories
            category_stats = await session.execute(
                select(
                    Strategy.category,
                    func.count(Strategy.id).label("count")
                ).where(Strategy.status == "approved")
                .group_by(Strategy.category)
                .order_by(desc("count"))
                .limit(5)
            )

            return {
                "total_strategies": total_strategies or 0,
                "published_strategies": published_strategies or 0,
                "total_purchases": total_purchases or 0,
                "total_revenue": float(total_revenue),
                "commission_earned": float(total_revenue * self.commission_rate),
                "top_categories": [
                    {"category": row.category, "count": row.count}
                    for row in category_stats
                ]
            }

    def _validate_strategy_code(self, code: str) -> bool:
        """Validate strategy code format"""
        # Basic validation - in production this would be more sophisticated
        if not code or len(code) < 10:
            return False

        # Check for required components
        required_keywords = ["def", "class", "return"]
        return any(keyword in code for keyword in required_keywords)

    async def _validate_strategy_for_publication(self, strategy: Strategy) -> dict[str, Any]:
        """Validate strategy before publication"""
        # In production, this would run comprehensive tests
        validation_issues = []

        if len(strategy.strategy_code) < 100:
            validation_issues.append("Strategy code too short")

        if not strategy.description or len(strategy.description) < 50:
            validation_issues.append("Description too short")

        if strategy.is_premium and strategy.price < Decimal(str(self.settings.MIN_STRATEGY_PRICE / 100)):
            validation_issues.append(f"Price too low (minimum ${self.settings.MIN_STRATEGY_PRICE / 100})")

        return {
            "valid": len(validation_issues) == 0,
            "reason": "; ".join(validation_issues) if validation_issues else None
        }

    async def _user_purchased_strategy(self, strategy_id: int, user_id: int) -> bool:
        """Check if user purchased strategy"""
        async with get_db_session() as session:
            purchase = await session.scalar(
                select(StrategyPurchase).where(
                    and_(
                        StrategyPurchase.strategy_id == strategy_id,
                        StrategyPurchase.buyer_id == user_id,
                        StrategyPurchase.status == "completed"
                    )
                )
            )
            return bool(purchase)

    async def _update_strategy_rating(self, strategy_id: int, session: AsyncSession):
        """Update strategy's average rating"""
        avg_rating = await session.scalar(
            select(func.avg(StrategyReview.rating)).where(
                StrategyReview.strategy_id == strategy_id
            )
        )

        review_count = await session.scalar(
            select(func.count(StrategyReview.id)).where(
                StrategyReview.strategy_id == strategy_id
            )
        )

        strategy = await session.get(Strategy, strategy_id)
        if strategy and avg_rating:
            strategy.rating = Decimal(str(round(float(avg_rating), 2)))
            strategy.review_count = review_count or 0
            strategy.updated_at = datetime.utcnow()

    async def _run_backtest_simulation(self, strategy: Strategy, params: dict[str, Any]) -> dict[str, Any]:
        """Run backtest simulation (mock implementation)"""
        # This would integrate with the actual trading bot's backtesting engine
        # For now, return mock results

        import random
        initial_balance = float(params["initial_balance"])

        # Mock results
        total_return = random.uniform(-0.2, 0.8)  # -20% to +80%
        final_balance = initial_balance * (1 + total_return)

        total_trades = random.randint(50, 500)
        winning_trades = int(total_trades * random.uniform(0.4, 0.7))
        losing_trades = total_trades - winning_trades

        return {
            "final_balance": final_balance,
            "total_return": total_return,
            "max_drawdown": random.uniform(0.05, 0.3),
            "win_rate": (winning_trades / total_trades) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "sharpe_ratio": random.uniform(0.5, 2.5),
            "trade_history": [],  # Would contain detailed trade data
            "equity_curve": []    # Would contain equity curve data
        }
