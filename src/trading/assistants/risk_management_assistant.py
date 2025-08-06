"""
Risk Management Assistant - Risk assessment and management helper
"""

import logging
import time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class RiskManagementAssistant:
    """Assistant for risk management operations"""

    def __init__(self, manager_or_config):
        # Handle both manager object and config dict
        if hasattr(manager_or_config, 'config'):
            self.manager = manager_or_config
            self.config = manager_or_config.config
        else:
            self.manager = None
            self.config = manager_or_config

        self.logger = logging.getLogger(__name__)
        self.max_position_size = self.config.get('max_position_size', 0.1)  # 10% of portfolio
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 0.02)  # 2% risk per trade

    def assess_position_risk(self, position_size: Decimal, portfolio_value: Decimal) -> Dict[str, Any]:
        """Assess risk level of a position"""
        try:
            if portfolio_value <= 0:
                return {
                    'risk_level': RiskLevel.EXTREME,
                    'risk_score': 1.0,
                    'reason': 'zero_portfolio_value'
                }

            position_ratio = float(position_size / portfolio_value)

            if position_ratio <= 0.05:  # 5%
                risk_level = RiskLevel.LOW
                risk_score = position_ratio / 0.05
            elif position_ratio <= 0.15:  # 15%
                risk_level = RiskLevel.MEDIUM
                risk_score = 0.5 + (position_ratio - 0.05) / 0.10 * 0.3
            elif position_ratio <= 0.25:  # 25%
                risk_level = RiskLevel.HIGH
                risk_score = 0.8 + (position_ratio - 0.15) / 0.10 * 0.15
            else:
                risk_level = RiskLevel.EXTREME
                risk_score = min(1.0, 0.95 + (position_ratio - 0.25) / 0.25 * 0.05)

            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'position_ratio': position_ratio,
                'reason': 'position_size_analysis'
            }

        except Exception as e:
            self.logger.error(f"Position risk assessment error: {e}")
            return {
                'risk_level': RiskLevel.EXTREME,
                'risk_score': 1.0,
                'reason': 'error'
            }

    def calculate_position_size(self, account_balance: Decimal, risk_percentage: float = 0.02) -> Decimal:
        """Calculate appropriate position size based on risk"""
        try:
            max_risk_amount = account_balance * Decimal(str(risk_percentage))
            return max_risk_amount

        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            return Decimal('0')

    def validate_trade_risk(self, trade_amount: Decimal, stop_loss_distance: Decimal,
                          account_balance: Decimal) -> Dict[str, Any]:
        """Validate if trade meets risk management criteria"""
        try:
            risk_amount = trade_amount * stop_loss_distance
            risk_percentage = float(risk_amount / account_balance)

            if risk_percentage <= self.max_risk_per_trade:
                return {
                    'approved': True,
                    'risk_percentage': risk_percentage,
                    'risk_amount': float(risk_amount),
                    'reason': 'within_risk_limits'
                }
            else:
                return {
                    'approved': False,
                    'risk_percentage': risk_percentage,
                    'risk_amount': float(risk_amount),
                    'reason': 'exceeds_risk_limits'
                }

        except Exception as e:
            self.logger.error(f"Trade risk validation error: {e}")
            return {
                'approved': False,
                'risk_percentage': 1.0,
                'risk_amount': 0.0,
                'reason': 'error'
            }

    def calculate_stop_loss(self, entry_price: Decimal, risk_percentage: float = 0.02) -> Decimal:
        """Calculate stop loss price based on risk"""
        try:
            stop_loss_distance = entry_price * Decimal(str(risk_percentage))
            stop_loss_price = entry_price - stop_loss_distance
            return max(stop_loss_price, Decimal('0'))

        except Exception as e:
            self.logger.error(f"Stop loss calculation error: {e}")
            return Decimal('0')

    def assess_market_risk(self, volatility: float, liquidity: float = 1.0) -> Dict[str, Any]:
        """Assess overall market risk conditions"""
        try:
            # Simple market risk assessment
            if volatility <= 0.02:  # 2% volatility
                risk_level = RiskLevel.LOW
            elif volatility <= 0.05:  # 5% volatility
                risk_level = RiskLevel.MEDIUM
            elif volatility <= 0.10:  # 10% volatility
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.EXTREME

            # Adjust for liquidity
            if liquidity < 0.5:
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM
                elif risk_level == RiskLevel.MEDIUM:
                    risk_level = RiskLevel.HIGH
                else:
                    risk_level = RiskLevel.EXTREME

            return {
                'risk_level': risk_level,
                'volatility': volatility,
                'liquidity': liquidity,
                'reason': 'market_conditions'
            }

        except Exception as e:
            self.logger.error(f"Market risk assessment error: {e}")
            return {
                'risk_level': RiskLevel.EXTREME,
                'volatility': 0.0,
                'liquidity': 0.0,
                'reason': 'error'
            }

    # ASYNC METHODS REQUIRED BY INFINITY TRADING MANAGER

    async def initialize(self):
        """Initialize the risk management assistant"""
        try:
            self.logger.info("[RISK_ASSISTANT] Initializing...")

            # Initialize risk parameters (tighter for user's optimized settings)
            self.risk_parameters = {
                'max_position_ratio': 0.08,  # 8% max position size
                'max_daily_loss': 0.05,      # 5% max daily loss
                'confidence_multiplier': 1.2, # Require higher confidence
                'volatility_threshold': 0.15,  # 15% volatility threshold
                'min_liquidity': 0.3,         # Minimum liquidity requirement
                'tighter_mode': False         # Can be adjusted dynamically
            }

            # Track risk state
            self.daily_pnl = 0.0
            self.active_positions_risk = 0.0
            self.last_reset = time.time()

            self.logger.info(f"[RISK_ASSISTANT] Initialized with max position ratio: {self.risk_parameters['max_position_ratio']:.1%}")

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Initialization error: {e}")

    async def stop(self):
        """Stop the risk management assistant"""
        try:
            self.logger.info("[RISK_ASSISTANT] Stopping...")

            # Final risk report
            if hasattr(self, 'daily_pnl'):
                self.logger.info(f"[RISK_ASSISTANT] Final daily PnL: ${self.daily_pnl:.2f}")

            self.logger.info("[RISK_ASSISTANT] Stopped successfully")

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Stop error: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the risk management assistant"""
        try:
            # Check if daily loss limits are breached
            max_daily_loss = self.risk_parameters.get('max_daily_loss', 0.05)
            daily_loss_breached = self.daily_pnl < -max_daily_loss

            # Check risk parameter integrity
            params_valid = all(
                isinstance(v, (int, float, bool)) for v in self.risk_parameters.values()
            )

            healthy = params_valid and not daily_loss_breached

            return {
                'healthy': healthy,
                'daily_pnl': getattr(self, 'daily_pnl', 0.0),
                'daily_loss_breached': daily_loss_breached,
                'parameters_valid': params_valid,
                'risk_parameters': getattr(self, 'risk_parameters', {}),
                'timestamp': time.time()
            }

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Health check error: {e}")
            return {'healthy': False, 'error': str(e)}

    async def validate_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate trading signals against risk criteria"""
        try:
            self.logger.debug(f"[RISK_ASSISTANT] Validating {len(signals)} signals")

            validated_signals = []

            if not signals:
                return validated_signals

            for signal in signals:
                try:
                    # Basic signal validation
                    if not self._validate_signal_structure(signal):
                        continue

                    # Risk-based validation
                    risk_check = await self._assess_signal_risk(signal)

                    if risk_check['approved']:
                        # Adjust signal based on risk parameters
                        adjusted_signal = self._adjust_signal_for_risk(signal, risk_check)
                        validated_signals.append(adjusted_signal)

                        self.logger.debug(f"[RISK_ASSISTANT] Validated signal for {signal.get('symbol')}: {risk_check['reason']}")
                    else:
                        self.logger.info(f"[RISK_ASSISTANT] Rejected signal for {signal.get('symbol')}: {risk_check['reason']}")

                except Exception as signal_error:
                    self.logger.warning(f"[RISK_ASSISTANT] Error validating signal {signal.get('symbol', 'unknown')}: {signal_error}")
                    continue

            self.logger.info(f"[RISK_ASSISTANT] Validated {len(validated_signals)}/{len(signals)} signals")
            return validated_signals

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Signal validation error: {e}")
            return []

    def _validate_signal_structure(self, signal: Dict[str, Any]) -> bool:
        """Validate signal has required structure"""
        required_fields = ['symbol', 'confidence', 'position_size_usd']
        return all(field in signal for field in required_fields)

    async def _assess_signal_risk(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk of individual signal"""
        try:
            # Check confidence against threshold
            confidence = signal.get('confidence', 0)
            required_confidence = 0.25 * self.risk_parameters.get('confidence_multiplier', 1.0)

            if confidence < required_confidence:
                return {
                    'approved': False,
                    'reason': f'Low confidence: {confidence:.3f} < {required_confidence:.3f}'
                }

            # Check position size
            position_size = signal.get('position_size_usd', 0)
            max_position = 50.0  # $50 max position (conservative for user's settings)

            if position_size > max_position:
                return {
                    'approved': False,
                    'reason': f'Position too large: ${position_size:.2f} > ${max_position:.2f}'
                }

            # Check daily loss limits
            if self.daily_pnl < -self.risk_parameters.get('max_daily_loss', 0.05) * 1000:  # Assume $1000 account
                return {
                    'approved': False,
                    'reason': f'Daily loss limit breached: ${self.daily_pnl:.2f}'
                }

            # Additional checks for tighter mode
            if self.risk_parameters.get('tighter_mode', False):
                required_confidence *= 1.5  # Even higher confidence in tighter mode
                max_position *= 0.7  # Smaller positions in tighter mode

                if confidence < required_confidence or position_size > max_position:
                    return {
                        'approved': False,
                        'reason': 'Tighter risk mode - higher requirements'
                    }

            return {
                'approved': True,
                'reason': 'Risk criteria met',
                'risk_score': 1.0 - confidence,  # Lower confidence = higher risk
                'position_size_approved': min(position_size, max_position)
            }

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Signal risk assessment error: {e}")
            return {
                'approved': False,
                'reason': f'Risk assessment error: {str(e)}'
            }

    def _adjust_signal_for_risk(self, signal: Dict[str, Any], risk_check: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust signal parameters based on risk assessment"""
        adjusted_signal = signal.copy()

        # Adjust position size if needed
        approved_size = risk_check.get('position_size_approved')
        if approved_size and approved_size < signal.get('position_size_usd', 0):
            adjusted_signal['position_size_usd'] = approved_size
            adjusted_signal['amount'] = approved_size / signal.get('price', 1)
            adjusted_signal['risk_adjusted'] = True

        # Add risk metadata
        adjusted_signal['risk_score'] = risk_check.get('risk_score', 0.5)
        adjusted_signal['risk_reason'] = risk_check.get('reason', '')

        return adjusted_signal

    async def adjust_risk_parameters(self, tighter: bool = True):
        """Adjust risk parameters based on market conditions"""
        try:
            if tighter:
                self.logger.info("[RISK_ASSISTANT] Tightening risk parameters")
                self.risk_parameters['tighter_mode'] = True
                self.risk_parameters['confidence_multiplier'] = 1.5
                self.risk_parameters['max_position_ratio'] *= 0.7
                self.risk_parameters['volatility_threshold'] *= 0.8
            else:
                self.logger.info("[RISK_ASSISTANT] Loosening risk parameters")
                self.risk_parameters['tighter_mode'] = False
                self.risk_parameters['confidence_multiplier'] = 1.0
                self.risk_parameters['max_position_ratio'] = min(0.08, self.risk_parameters['max_position_ratio'] / 0.7)
                self.risk_parameters['volatility_threshold'] = min(0.15, self.risk_parameters['volatility_threshold'] / 0.8)

            self.logger.info(f"[RISK_ASSISTANT] Risk parameters adjusted - tighter mode: {self.risk_parameters['tighter_mode']}")

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Error adjusting risk parameters: {e}")

    async def update_daily_pnl(self, pnl_change: float):
        """Update daily PnL tracking"""
        try:
            current_time = time.time()

            # Reset daily PnL if it's a new day
            if current_time - self.last_reset > 86400:  # 24 hours
                self.daily_pnl = 0.0
                self.last_reset = current_time
                self.logger.info("[RISK_ASSISTANT] Daily PnL reset for new day")

            self.daily_pnl += pnl_change
            self.logger.debug(f"[RISK_ASSISTANT] Daily PnL updated: ${self.daily_pnl:.2f} (+${pnl_change:.2f})")

        except Exception as e:
            self.logger.error(f"[RISK_ASSISTANT] Error updating daily PnL: {e}")
