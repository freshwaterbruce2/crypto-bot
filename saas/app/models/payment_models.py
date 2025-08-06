"""
Payment Processing Models
========================

Database models for payments, billing, invoices, and financial transactions.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ..core.database import Base


class Payment(Base):
    """Payment transaction records"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Payment details
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(String(50), nullable=False)  # stripe, crypto, bank_transfer

    # Transaction info
    transaction_id = Column(String(100), unique=True, nullable=False)
    external_id = Column(String(100), nullable=True)  # Stripe payment intent ID, crypto tx hash

    # Payment purpose
    payment_type = Column(String(50), nullable=False)  # subscription, strategy_purchase, white_label
    reference_id = Column(String(100), nullable=True)  # Subscription ID, Strategy ID, etc.

    # Status tracking
    status = Column(String(20), default="pending")  # pending, completed, failed, refunded, cancelled
    failure_reason = Column(Text, nullable=True)

    # Stripe specific
    stripe_payment_intent_id = Column(String(100), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)

    # Cryptocurrency specific
    crypto_currency = Column(String(10), nullable=True)  # BTC, ETH, etc.
    crypto_address = Column(String(100), nullable=True)
    crypto_tx_hash = Column(String(100), nullable=True)
    crypto_confirmations = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payments")
    refunds = relationship("PaymentRefund", back_populates="payment")

    @hybrid_property
    def is_completed(self) -> bool:
        """Check if payment is completed"""
        return self.status == "completed"

    @hybrid_property
    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self.status == "pending"

    @hybrid_property
    def total_refunded(self) -> Decimal:
        """Calculate total refunded amount"""
        if not self.refunds:
            return Decimal("0.00")

        return sum(refund.amount for refund in self.refunds if refund.status == "completed")

    def to_dict(self) -> dict:
        """Convert payment to dictionary"""
        return {
            "id": self.id,
            "amount": float(self.amount),
            "currency": self.currency,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "payment_type": self.payment_type,
            "status": self.status,
            "is_completed": self.is_completed,
            "is_pending": self.is_pending,
            "total_refunded": float(self.total_refunded),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PaymentRefund(Base):
    """Payment refund records"""
    __tablename__ = "payment_refunds"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)

    # Refund details
    amount = Column(Numeric(15, 2), nullable=False)
    reason = Column(String(200), nullable=True)

    # External references
    stripe_refund_id = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    payment = relationship("Payment", back_populates="refunds")


class Invoice(Base):
    """Invoice generation and tracking"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    tax_amount = Column(Numeric(15, 2), default=0)

    # Billing information
    billing_name = Column(String(200), nullable=False)
    billing_email = Column(String(255), nullable=False)
    billing_address = Column(JSON, default=dict)

    # Line items
    line_items = Column(JSON, default=list)

    # Dates
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft, sent, paid, overdue, cancelled

    # Payment tracking
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)

    # Files
    pdf_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    payment = relationship("Payment")


class PaymentMethod(Base):
    """Stored payment methods for users"""
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Payment method details
    type = Column(String(20), nullable=False)  # card, bank_account, crypto_wallet
    provider = Column(String(50), nullable=False)  # stripe, coinbase, etc.

    # Card details (masked)
    last_four = Column(String(4), nullable=True)
    brand = Column(String(20), nullable=True)  # visa, mastercard, etc.
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)

    # External references
    stripe_payment_method_id = Column(String(100), nullable=True)

    # Crypto wallet details
    crypto_currency = Column(String(10), nullable=True)
    wallet_address = Column(String(100), nullable=True)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


class CryptoPayment(Base):
    """Cryptocurrency payment tracking"""
    __tablename__ = "crypto_payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)

    # Crypto details
    currency = Column(String(10), nullable=False)  # BTC, ETH, USDT, etc.
    amount_crypto = Column(Numeric(20, 8), nullable=False)
    amount_usd = Column(Numeric(15, 2), nullable=False)
    exchange_rate = Column(Numeric(20, 8), nullable=False)

    # Addresses
    deposit_address = Column(String(100), nullable=False)
    from_address = Column(String(100), nullable=True)

    # Transaction details
    tx_hash = Column(String(100), nullable=True)
    block_height = Column(Integer, nullable=True)
    confirmations = Column(Integer, default=0)
    required_confirmations = Column(Integer, default=3)

    # Status
    status = Column(String(20), default="pending")  # pending, confirmed, failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    payment = relationship("Payment")


class Payout(Base):
    """Payouts to strategy creators and partners"""
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Payout details
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payout_method = Column(String(50), nullable=False)  # stripe, paypal, bank_transfer, crypto

    # Period covered
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Revenue breakdown
    strategy_sales = Column(Numeric(15, 2), default=0)
    commission_earned = Column(Numeric(15, 2), default=0)
    bonus_amount = Column(Numeric(15, 2), default=0)

    # External references
    stripe_transfer_id = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")


class BillingAddress(Base):
    """User billing addresses"""
    __tablename__ = "billing_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Address details
    company = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False)
    line1 = Column(String(200), nullable=False)
    line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(2), nullable=False)  # ISO country code

    # Tax information
    tax_id = Column(String(50), nullable=True)
    tax_id_type = Column(String(20), nullable=True)  # vat, ein, etc.

    # Status
    is_default = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
