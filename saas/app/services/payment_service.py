"""
Payment Processing Service
=========================

Service layer for payment processing, billing, and financial transactions.
Integrates with Stripe and cryptocurrency payment providers.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import stripe
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import get_db_session
from ..models.payment_models import CryptoPayment, Invoice, Payment, PaymentRefund
from ..models.subscription_models import Subscription
from ..models.user_models import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Stripe
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    """Payment processing service"""

    def __init__(self):
        self.settings = get_settings()
        self.stripe_enabled = bool(self.settings.STRIPE_SECRET_KEY)
        self.crypto_enabled = self.settings.CRYPTO_PAYMENT_ENABLED

    async def create_payment_intent(
        self,
        user_id: int,
        amount: float,
        currency: str = "USD",
        payment_type: str = "subscription",
        reference_id: str = None,
        metadata: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Create Stripe payment intent"""
        if not self.stripe_enabled:
            raise ValueError("Stripe is not configured")

        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            # Create payment record
            payment = Payment(
                user_id=user_id,
                amount=Decimal(str(amount)),
                currency=currency,
                payment_method="stripe",
                transaction_id=f"pending_{datetime.utcnow().timestamp()}",
                payment_type=payment_type,
                reference_id=reference_id,
                status="pending",
                metadata=metadata or {}
            )

            session.add(payment)
            await session.flush()

            try:
                # Create Stripe payment intent
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),  # Stripe uses cents
                    currency=currency.lower(),
                    customer=await self._get_or_create_stripe_customer(user),
                    metadata={
                        "user_id": str(user_id),
                        "payment_id": str(payment.id),
                        "payment_type": payment_type,
                        "reference_id": reference_id or "",
                        **(metadata or {})
                    },
                    automatic_payment_methods={"enabled": True}
                )

                # Update payment with Stripe details
                payment.stripe_payment_intent_id = intent.id
                payment.transaction_id = intent.id
                payment.external_id = intent.id

                await session.commit()

                return {
                    "payment_id": payment.id,
                    "client_secret": intent.client_secret,
                    "stripe_payment_intent_id": intent.id,
                    "amount": amount,
                    "currency": currency
                }

            except stripe.StripeError as e:
                payment.status = "failed"
                payment.failure_reason = str(e)
                payment.failed_at = datetime.utcnow()
                await session.commit()
                raise ValueError(f"Payment intent creation failed: {str(e)}")

    async def confirm_payment(self, payment_id: int, stripe_payment_intent_id: str) -> Payment:
        """Confirm payment completion"""
        async with get_db_session() as session:
            payment = await session.get(Payment, payment_id)
            if not payment:
                raise ValueError("Payment not found")

            if self.stripe_enabled:
                try:
                    # Retrieve payment intent from Stripe
                    intent = stripe.PaymentIntent.retrieve(stripe_payment_intent_id)

                    if intent.status == "succeeded":
                        payment.status = "completed"
                        payment.completed_at = datetime.utcnow()

                        # Process the payment based on type
                        await self._process_completed_payment(payment, session)

                    elif intent.status == "payment_failed":
                        payment.status = "failed"
                        payment.failure_reason = intent.last_payment_error.get("message") if intent.last_payment_error else "Payment failed"
                        payment.failed_at = datetime.utcnow()

                except stripe.StripeError as e:
                    logger.error(f"Error confirming payment {payment_id}: {e}")
                    payment.status = "failed"
                    payment.failure_reason = str(e)
                    payment.failed_at = datetime.utcnow()

            await session.commit()
            return payment

    async def create_crypto_payment(
        self,
        user_id: int,
        amount_usd: float,
        crypto_currency: str = "BTC",
        payment_type: str = "subscription",
        reference_id: str = None
    ) -> dict[str, Any]:
        """Create cryptocurrency payment"""
        if not self.crypto_enabled:
            raise ValueError("Cryptocurrency payments are not enabled")

        async with get_db_session() as session:
            # Generate unique deposit address (in production, use a proper crypto service)
            deposit_address = self._generate_crypto_address(crypto_currency)

            # Get current exchange rate (in production, use a real price feed)
            exchange_rate = await self._get_crypto_exchange_rate(crypto_currency)
            amount_crypto = Decimal(str(amount_usd)) / exchange_rate

            # Create payment record
            payment = Payment(
                user_id=user_id,
                amount=Decimal(str(amount_usd)),
                currency="USD",
                payment_method="crypto",
                transaction_id=f"crypto_{datetime.utcnow().timestamp()}",
                payment_type=payment_type,
                reference_id=reference_id,
                status="pending",
                crypto_currency=crypto_currency
            )

            session.add(payment)
            await session.flush()

            # Create crypto payment record
            crypto_payment = CryptoPayment(
                payment_id=payment.id,
                currency=crypto_currency,
                amount_crypto=amount_crypto,
                amount_usd=Decimal(str(amount_usd)),
                exchange_rate=exchange_rate,
                deposit_address=deposit_address,
                expires_at=datetime.utcnow() + timedelta(hours=2)  # 2 hour expiry
            )

            session.add(crypto_payment)
            await session.commit()

            return {
                "payment_id": payment.id,
                "deposit_address": deposit_address,
                "amount_crypto": float(amount_crypto),
                "amount_usd": amount_usd,
                "currency": crypto_currency,
                "exchange_rate": float(exchange_rate),
                "expires_at": crypto_payment.expires_at.isoformat()
            }

    async def process_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Process Stripe webhook"""
        if not self.stripe_enabled:
            return {"status": "ignored", "reason": "Stripe not configured"}

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            return {"status": "error", "reason": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return {"status": "error", "reason": "Invalid signature"}

        # Handle the event
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            await self._handle_payment_success(payment_intent)

        elif event["type"] == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            await self._handle_payment_failure(payment_intent)

        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            await self._handle_subscription_payment(invoice)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await self._handle_subscription_cancellation(subscription)

        return {"status": "processed", "event_type": event["type"]}

    async def create_refund(
        self,
        payment_id: int,
        amount: Optional[float] = None,
        reason: str = None
    ) -> PaymentRefund:
        """Create payment refund"""
        async with get_db_session() as session:
            payment = await session.get(Payment, payment_id)
            if not payment:
                raise ValueError("Payment not found")

            if payment.status != "completed":
                raise ValueError("Can only refund completed payments")

            refund_amount = Decimal(str(amount)) if amount else payment.amount

            if refund_amount > payment.amount:
                raise ValueError("Refund amount cannot exceed payment amount")

            # Check existing refunds
            existing_refunds = sum(r.amount for r in payment.refunds if r.status == "completed")
            if existing_refunds + refund_amount > payment.amount:
                raise ValueError("Total refunds cannot exceed payment amount")

            # Create refund record
            refund = PaymentRefund(
                payment_id=payment_id,
                amount=refund_amount,
                reason=reason,
                status="pending"
            )

            session.add(refund)
            await session.flush()

            if self.stripe_enabled and payment.stripe_payment_intent_id:
                try:
                    # Create Stripe refund
                    stripe_refund = stripe.Refund.create(
                        payment_intent=payment.stripe_payment_intent_id,
                        amount=int(refund_amount * 100),  # Stripe uses cents
                        reason=reason or "requested_by_customer"
                    )

                    refund.stripe_refund_id = stripe_refund.id
                    refund.status = "completed"
                    refund.completed_at = datetime.utcnow()

                except stripe.StripeError as e:
                    refund.status = "failed"
                    logger.error(f"Stripe refund failed: {e}")
                    raise ValueError(f"Refund failed: {str(e)}")

            await session.commit()
            return refund

    async def get_user_payments(
        self,
        user_id: int,
        status: str = None,
        payment_type: str = None,
        limit: int = 50
    ) -> list[Payment]:
        """Get user's payment history"""
        async with get_db_session() as session:
            stmt = select(Payment).where(Payment.user_id == user_id)

            if status:
                stmt = stmt.where(Payment.status == status)

            if payment_type:
                stmt = stmt.where(Payment.payment_type == payment_type)

            stmt = stmt.order_by(Payment.created_at.desc()).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def generate_invoice(
        self,
        user_id: int,
        line_items: list[dict[str, Any]],
        due_days: int = 30
    ) -> Invoice:
        """Generate invoice for user"""
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            # Calculate totals
            subtotal = sum(Decimal(str(item["amount"])) for item in line_items)
            tax_amount = subtotal * Decimal("0.08")  # 8% tax (configurable)
            total_amount = subtotal + tax_amount

            # Generate invoice number
            invoice_count = await session.scalar(select(func.count(Invoice.id)))
            invoice_number = f"INV-{datetime.now().year}-{(invoice_count or 0) + 1:06d}"

            invoice = Invoice(
                user_id=user_id,
                invoice_number=invoice_number,
                amount=total_amount,
                tax_amount=tax_amount,
                billing_name=user.full_name or user.username,
                billing_email=user.email,
                line_items=line_items,
                due_date=datetime.utcnow() + timedelta(days=due_days),
                status="sent"
            )

            session.add(invoice)
            await session.commit()
            return invoice

    async def get_revenue_stats(self, days: int = 30) -> dict[str, Any]:
        """Get revenue statistics"""
        async with get_db_session() as session:
            since_date = datetime.utcnow() - timedelta(days=days)

            # Total revenue
            total_revenue = await session.scalar(
                select(func.sum(Payment.amount)).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at >= since_date
                    )
                )
            ) or Decimal("0")

            # Revenue by payment type
            revenue_by_type = await session.execute(
                select(
                    Payment.payment_type,
                    func.sum(Payment.amount).label("total")
                ).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at >= since_date
                    )
                ).group_by(Payment.payment_type)
            )

            # Payment method distribution
            payment_methods = await session.execute(
                select(
                    Payment.payment_method,
                    func.count(Payment.id).label("count"),
                    func.sum(Payment.amount).label("total")
                ).where(
                    and_(
                        Payment.status == "completed",
                        Payment.created_at >= since_date
                    )
                ).group_by(Payment.payment_method)
            )

            return {
                "period_days": days,
                "total_revenue": float(total_revenue),
                "revenue_by_type": {row.payment_type: float(row.total) for row in revenue_by_type},
                "payment_methods": [
                    {
                        "method": row.payment_method,
                        "count": row.count,
                        "total": float(row.total)
                    }
                    for row in payment_methods
                ]
            }

    async def _get_or_create_stripe_customer(self, user: User) -> str:
        """Get or create Stripe customer"""
        if user.subscription and user.subscription.stripe_customer_id:
            return user.subscription.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)}
        )

        # Update user's subscription with customer ID
        if user.subscription:
            async with get_db_session() as session:
                subscription = await session.get(Subscription, user.subscription.id)
                if subscription:
                    subscription.stripe_customer_id = customer.id
                    await session.commit()

        return customer.id

    async def _process_completed_payment(self, payment: Payment, session: AsyncSession):
        """Process completed payment based on type"""
        if payment.payment_type == "subscription":
            from .subscription_service import SubscriptionService
            subscription_service = SubscriptionService()

            # Upgrade subscription if reference_id contains tier info
            if payment.reference_id:
                parts = payment.reference_id.split(":")
                if len(parts) >= 2:
                    tier_name = parts[0]
                    billing_cycle = parts[1]

                    await subscription_service.upgrade_subscription(
                        payment.user_id,
                        tier_name,
                        billing_cycle,
                        payment.stripe_payment_intent_id
                    )

        elif payment.payment_type == "strategy_purchase":
            # Handle strategy purchase
            pass  # Will be implemented in strategy service

    async def _handle_payment_success(self, payment_intent):
        """Handle successful payment webhook"""
        payment_id = payment_intent["metadata"].get("payment_id")
        if payment_id:
            await self.confirm_payment(int(payment_id), payment_intent["id"])

    async def _handle_payment_failure(self, payment_intent):
        """Handle failed payment webhook"""
        payment_id = payment_intent["metadata"].get("payment_id")
        if payment_id:
            async with get_db_session() as session:
                payment = await session.get(Payment, int(payment_id))
                if payment:
                    payment.status = "failed"
                    payment.failure_reason = payment_intent.get("last_payment_error", {}).get("message", "Payment failed")
                    payment.failed_at = datetime.utcnow()
                    await session.commit()

    async def _handle_subscription_payment(self, invoice):
        """Handle subscription payment webhook"""
        # This would be called for recurring subscription payments
        pass

    async def _handle_subscription_cancellation(self, subscription):
        """Handle subscription cancellation webhook"""
        # This would be called when a subscription is cancelled in Stripe
        pass

    def _generate_crypto_address(self, currency: str) -> str:
        """Generate crypto deposit address (mock implementation)"""
        # In production, this would integrate with a proper crypto service
        import secrets
        if currency == "BTC":
            return f"bc1q{secrets.token_hex(20)}"
        elif currency == "ETH":
            return f"0x{secrets.token_hex(20)}"
        else:
            return f"{currency.lower()}_{secrets.token_hex(16)}"

    async def _get_crypto_exchange_rate(self, currency: str) -> Decimal:
        """Get cryptocurrency exchange rate (mock implementation)"""
        # In production, this would call a real price API
        rates = {
            "BTC": Decimal("45000.00"),
            "ETH": Decimal("3000.00"),
            "USDT": Decimal("1.00")
        }
        return rates.get(currency, Decimal("1.00"))
