"""
Position Sizing Utilities for Small Account Optimization
========================================================

This module provides position sizing algorithms specifically optimized
for small trading accounts with low balance optimization features.

Key Features:
- Small account position sizing with $1.00 minimums
- SHIB/USDT token amount calculations  
- Dynamic sizing based on account balance
- Risk management for micro-accounts
- Compound growth optimization
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_DOWN
from ..config.constants import calculate_minimum_cost, MINIMUM_ORDER_SIZE_TIER1
from ..config.kraken_precision_config import (
    get_precision_config, format_price, format_volume, validate_order_params
)

logger = logging.getLogger(__name__)


def calculate_position_size_for_small_account(
    account_balance: float,
    symbol: str,
    risk_percentage: float = 0.95,
    min_order_size_usd: float = None,
    config: Optional[Dict[str, Any]] = None,
    current_price: float = None
) -> Dict[str, Any]:
    """
    Calculate optimal position size for small accounts with Kraken compliance
    
    Args:
        account_balance: Total account balance in USD
        symbol: Trading pair symbol (e.g., 'SHIB/USDT')
        risk_percentage: Percentage of account to risk (default 95% for aggressive deployment)
        min_order_size_usd: Minimum order size in USD (auto-calculated if None)
        config: Configuration dictionary with additional settings
        current_price: Current asset price for minimum calculation
        
    Returns:
        Dict with position sizing information
    """
    try:
        logger.debug(f"[POSITION_SIZING] Calculating for ${account_balance:.2f} account, {symbol}")
        
        config = config or {}
        
        # Extract asset from symbol for tier-1 detection
        if '/' in symbol:
            base_asset = symbol.split('/')[0]
        else:
            base_asset = symbol.replace('USDT', '')
        
        # Calculate Kraken-compliant minimum order size
        if min_order_size_usd is None:
            if current_price is not None:
                min_order_size_usd = calculate_minimum_cost(base_asset, current_price, 'pro')
            else:
                # Use tier-1 minimum as fallback for SHIB and similar assets
                tier1_assets = ['SHIB', 'DOGE', 'ADA', 'XRP', 'ALGO', 'MATIC']
                min_order_size_usd = MINIMUM_ORDER_SIZE_TIER1 if base_asset.upper() in tier1_assets else 1.0
        
        # Base calculations
        max_deployable = account_balance * risk_percentage
        
        # Ensure we meet minimum order requirements
        if max_deployable < min_order_size_usd:
            return {
                'success': False,
                'reason': f'Deployable amount ${max_deployable:.2f} below minimum ${min_order_size_usd}',
                'account_balance': account_balance,
                'deployable_amount': max_deployable,
                'min_required': min_order_size_usd
            }
        
        # SHIB/USDT specific calculations
        if symbol == 'SHIB/USDT':
            return _calculate_shib_position_size(
                max_deployable, account_balance, config
            )
        
        # General position sizing for other pairs
        return _calculate_general_position_size(
            max_deployable, account_balance, symbol, config
        )
        
    except Exception as e:
        logger.error(f"[POSITION_SIZING] Error calculating position size: {e}")
        return {
            'success': False,
            'error': str(e),
            'account_balance': account_balance,
            'symbol': symbol
        }


def _calculate_shib_position_size(
    deployable_amount: float,
    account_balance: float,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate SHIB-specific position sizes with Kraken precision requirements"""
    
    # Get Kraken precision config for SHIB/USDT
    precision_config = get_precision_config('SHIB/USDT')
    
    # SHIB price approximation (this would be real-time in production)
    shib_price = 0.00001  # $0.00001 per SHIB token
    
    # Use Kraken's official minimum volume requirement
    min_order_shib = precision_config['min_volume']  # 160,000 SHIB minimum
    
    # Calculate maximum SHIB tokens we can buy
    max_shib_tokens = deployable_amount / shib_price
    
    # Ensure we meet Kraken minimum SHIB order requirements
    if max_shib_tokens < min_order_shib:
        required_usd = min_order_shib * shib_price
        return {
            'success': False,
            'reason': f'Can buy {max_shib_tokens:.0f} SHIB, need minimum {min_order_shib}',
            'max_shib_tokens': max_shib_tokens,
            'min_shib_required': min_order_shib,
            'required_usd': required_usd,
            'available_usd': deployable_amount
        }
    
    # Calculate position tiers for diversification
    position_tiers = _calculate_shib_position_tiers(deployable_amount, max_shib_tokens)
    
    return {
        'success': True,
        'symbol': 'SHIB/USDT',
        'account_balance': account_balance,
        'deployable_amount': deployable_amount,
        'shib_price': shib_price,
        'max_shib_tokens': max_shib_tokens,
        'min_shib_required': min_order_shib,
        'position_tiers': position_tiers,
        'recommended_position': position_tiers[0],  # Largest position
        'compound_growth_potential': _calculate_compound_potential(deployable_amount)
    }


def _calculate_general_position_size(
    deployable_amount: float,
    account_balance: float,
    symbol: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate position sizes for non-SHIB pairs"""
    
    # Extract base and quote assets
    if '/' in symbol:
        base_asset, quote_asset = symbol.split('/')
    else:
        base_asset = symbol.replace('USDT', '')
        quote_asset = 'USDT'
    
    # Conservative position sizing for small accounts
    position_tiers = [
        {'size_usd': deployable_amount * 0.6, 'description': 'primary_position'},
        {'size_usd': deployable_amount * 0.25, 'description': 'secondary_position'},
        {'size_usd': deployable_amount * 0.15, 'description': 'reserve_position'}
    ]
    
    # Filter out positions below minimum
    min_order_size = config.get('min_order_size_usdt', 1.0)
    valid_tiers = [tier for tier in position_tiers if tier['size_usd'] >= min_order_size]
    
    return {
        'success': True,
        'symbol': symbol,
        'base_asset': base_asset,
        'quote_asset': quote_asset,
        'account_balance': account_balance,
        'deployable_amount': deployable_amount,
        'position_tiers': valid_tiers,
        'recommended_position': valid_tiers[0] if valid_tiers else None,
        'min_order_size': min_order_size
    }


def _calculate_shib_position_tiers(deployable_amount: float, max_tokens: float) -> list:
    """Calculate SHIB position tiers for progressive deployment"""
    
    tiers = []
    
    # Tier 1: 60% of deployable (aggressive primary position)
    tier1_usd = deployable_amount * 0.6
    tier1_tokens = tier1_usd / 0.00001
    if tier1_usd >= 1.0:  # Must meet minimum
        tiers.append({
            'size_usd': tier1_usd,
            'shib_tokens': tier1_tokens,
            'percentage': 60,
            'description': 'primary_aggressive'
        })
    
    # Tier 2: 25% of deployable (secondary position)
    tier2_usd = deployable_amount * 0.25
    tier2_tokens = tier2_usd / 0.00001
    if tier2_usd >= 1.0:
        tiers.append({
            'size_usd': tier2_usd,
            'shib_tokens': tier2_tokens,
            'percentage': 25,
            'description': 'secondary_position'
        })
    
    # Tier 3: 15% of deployable (reserve/DCA)
    tier3_usd = deployable_amount * 0.15
    tier3_tokens = tier3_usd / 0.00001
    if tier3_usd >= 1.0:
        tiers.append({
            'size_usd': tier3_usd,
            'shib_tokens': tier3_tokens,
            'percentage': 15,
            'description': 'reserve_dca'
        })
    
    return tiers


def _calculate_compound_potential(initial_amount: float) -> Dict[str, Any]:
    """Calculate compound growth potential for micro-profit trading"""
    
    # Micro-profit parameters
    profit_rate = 0.002  # 0.2% per trade
    trades_per_day = 50   # Aggressive micro-scalping
    
    # Calculate daily compound growth
    current_balance = initial_amount
    daily_balances = []
    
    for day in range(7):  # One week projection
        daily_trades = trades_per_day
        for trade in range(daily_trades):
            profit = current_balance * profit_rate
            current_balance += profit
        
        daily_balances.append({
            'day': day + 1,
            'balance': current_balance,
            'profit': current_balance - initial_amount,
            'growth_pct': ((current_balance / initial_amount) - 1) * 100
        })
    
    weekly_growth = ((current_balance / initial_amount) - 1) * 100
    
    return {
        'initial_amount': initial_amount,
        'profit_per_trade': profit_rate,
        'trades_per_day': trades_per_day,
        'weekly_projection': current_balance,
        'weekly_growth_pct': weekly_growth,
        'daily_progression': daily_balances[:3],  # First 3 days
        'compound_effective': weekly_growth > 10.0  # >10% weekly growth
    }


def calculate_shib_token_amount(usd_amount: float, shib_price: float = 0.00001) -> Dict[str, Any]:
    """
    Calculate SHIB token amounts for USD values
    
    Args:
        usd_amount: USD amount to convert
        shib_price: Current SHIB price in USD
        
    Returns:
        Dict with token calculations
    """
    try:
        # Calculate SHIB tokens
        shib_tokens = usd_amount / shib_price
        
        # Check minimum order requirements
        min_shib_tokens = 100000  # 100k SHIB minimum
        meets_minimum = shib_tokens >= min_shib_tokens
        
        return {
            'usd_amount': usd_amount,
            'shib_price': shib_price,
            'shib_tokens': shib_tokens,
            'shib_tokens_formatted': f"{shib_tokens:,.0f}",
            'min_shib_required': min_shib_tokens,
            'meets_minimum': meets_minimum,
            'token_value_check': usd_amount >= 1.0  # $1 minimum
        }
        
    except Exception as e:
        logger.error(f"[POSITION_SIZING] Error calculating SHIB tokens: {e}")
        return {
            'error': str(e),
            'usd_amount': usd_amount,
            'shib_price': shib_price
        }


def validate_position_size_constraints(
    position_size: float,
    symbol: str,
    account_balance: float,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate position size against all constraints
    
    Args:
        position_size: Proposed position size in USD
        symbol: Trading pair symbol
        account_balance: Total account balance
        config: Configuration with limits and constraints
        
    Returns:
        Dict with validation results
    """
    config = config or {}
    
    # Basic constraints
    min_order_size = config.get('min_order_size_usdt', 1.0)
    max_deployment_pct = config.get('max_capital_deployment_pct', 0.95)
    
    max_position_size = account_balance * max_deployment_pct
    
    # Validation checks
    validation_results = {
        'valid': True,
        'position_size': position_size,
        'constraints_checked': [],
        'warnings': [],
        'errors': []
    }
    
    # Check minimum size
    if position_size < min_order_size:
        validation_results['valid'] = False
        validation_results['errors'].append(
            f'Position ${position_size:.2f} below minimum ${min_order_size}'
        )
    
    validation_results['constraints_checked'].append('minimum_size')
    
    # Check maximum deployment
    if position_size > max_position_size:
        validation_results['valid'] = False
        validation_results['errors'].append(
            f'Position ${position_size:.2f} exceeds max ${max_position_size:.2f} ({max_deployment_pct:.0%} of account)'
        )
    
    validation_results['constraints_checked'].append('maximum_deployment')
    
    # SHIB-specific validations
    if symbol == 'SHIB/USDT':
        shib_validation = _validate_shib_constraints(position_size, config)
        validation_results['shib_constraints'] = shib_validation
        
        if not shib_validation['valid']:
            validation_results['valid'] = False
            validation_results['errors'].extend(shib_validation['errors'])
    
    # Risk warnings
    risk_pct = (position_size / account_balance) * 100
    if risk_pct > 80:
        validation_results['warnings'].append(
            f'High risk: {risk_pct:.1f}% of account in single position'
        )
    
    return validation_results


def _validate_shib_constraints(position_size: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate SHIB-specific constraints"""
    
    single_pair_config = config.get('single_pair_focus', {})
    min_order_shib = single_pair_config.get('min_order_shib', 100000)
    shib_price = 0.00001
    
    # Calculate SHIB tokens for position
    shib_tokens = position_size / shib_price
    
    validation = {
        'valid': True,
        'errors': [],
        'shib_tokens': shib_tokens,
        'min_shib_required': min_order_shib
    }
    
    if shib_tokens < min_order_shib:
        validation['valid'] = False
        validation['errors'].append(
            f'SHIB tokens {shib_tokens:.0f} below minimum {min_order_shib}'
        )
    
    return validation


def calculate_position_size(
    account_balance: float,
    symbol: str,
    risk_percentage: float = 0.95,
    min_order_size_usd: float = 1.0,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for calculate_position_size_for_small_account
    
    This function maintains compatibility with existing strategy imports
    while delegating to the main position sizing function.
    """
    return calculate_position_size_for_small_account(
        account_balance=account_balance,
        symbol=symbol,
        risk_percentage=risk_percentage,
        min_order_size_usd=min_order_size_usd,
        config=config
    )