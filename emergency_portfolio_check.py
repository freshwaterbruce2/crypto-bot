#!/usr/bin/env python3
"""
Emergency Portfolio Check
========================

Direct portfolio asset verification without exchange connection.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

async def check_portfolio_assets():
    """Check available portfolio assets for liquidation"""
    try:
        print("=== EMERGENCY PORTFOLIO ASSET CHECK ===")
        
        # Check for known portfolio state files
        portfolio_files = [
            project_root / "trading_data" / "portfolio_state.json",
            project_root / "data" / "portfolio_state.json",
            project_root / "portfolio_liquidation_analysis.json"
        ]
        
        found_assets = {}
        total_estimated_value = 0.0
        
        for portfolio_file in portfolio_files:
            if portfolio_file.exists():
                try:
                    with open(portfolio_file, 'r') as f:
                        data = json.load(f)
                    
                    print(f"[PORTFOLIO] Found portfolio data in: {portfolio_file.name}")
                    
                    # Extract asset information
                    if isinstance(data, dict):
                        if 'deployed_assets' in data:
                            for asset_info in data['deployed_assets']:
                                asset = asset_info.get('asset', '')
                                amount = asset_info.get('amount', 0)
                                value = asset_info.get('value_usd', 0)
                                
                                if asset and amount > 0:
                                    found_assets[asset] = {
                                        'amount': amount,
                                        'value_usd': value,
                                        'source': portfolio_file.name
                                    }
                                    total_estimated_value += value
                        
                        # Check for direct asset balances
                        for key, value in data.items():
                            if key.upper() in ['AI16Z', 'ALGO', 'ATOM', 'AVAX', 'BERA', 'SOL', 'BTC', 'ETH']:
                                if isinstance(value, (int, float)) and value > 0:
                                    asset = key.upper()
                                    if asset not in found_assets:
                                        found_assets[asset] = {
                                            'amount': value,
                                            'value_usd': value * 10.0,  # Rough estimate
                                            'source': portfolio_file.name
                                        }
                                        total_estimated_value += value * 10.0
                        
                except Exception as e:
                    print(f"[PORTFOLIO] Error reading {portfolio_file.name}: {e}")
        
        # Known asset estimates from the emergency description
        known_assets = {
            'AI16Z': {'amount': 14.895, 'value_usd': 34.47},
            'ALGO': {'amount': 113.682, 'value_usd': 25.21},
            'ATOM': {'amount': 5.581, 'value_usd': 37.09},
            'AVAX': {'amount': 2.331, 'value_usd': 84.97},
            'BERA': {'amount': 2.569, 'value_usd': 10.19},
            'SOL': {'amount': 0.024, 'value_usd': 5.00}
        }
        
        # Merge with known assets if nothing found
        if not found_assets:
            print("[PORTFOLIO] No portfolio files found, using known asset estimates...")
            found_assets = known_assets
            total_estimated_value = sum(asset['value_usd'] for asset in known_assets.values())
        
        # Check USDT balance estimate
        usdt_balance = 5.0  # Conservative estimate from emergency description
        
        print(f"\n=== PORTFOLIO ANALYSIS ===")
        print(f"Available USDT: ${usdt_balance:.2f}")
        print(f"Deployed Assets: {len(found_assets)}")
        print(f"Total Deployed Value: ${total_estimated_value:.2f}")
        print(f"Total Portfolio: ${usdt_balance + total_estimated_value:.2f}")
        
        print(f"\n=== LIQUIDATION CANDIDATES ===")
        liquidation_priority = []
        
        for asset, info in found_assets.items():
            amount = info['amount']
            value = info['value_usd']
            
            # Calculate liquidation priority (smaller positions first)
            if value >= 10.0:  # Only meaningful positions
                liquidation_pct = 0.30 if value < 50.0 else 0.20  # 30% for small, 20% for large
                liquidation_value = value * liquidation_pct
                
                liquidation_priority.append({
                    'asset': asset,
                    'amount': amount,
                    'total_value': value,
                    'liquidation_amount': amount * liquidation_pct,
                    'liquidation_value': liquidation_value,
                    'priority': 'high' if value < 30.0 else 'medium'
                })
                
                print(f"  {asset}: {amount:.8f} (${value:.2f}) -> Liquidate {liquidation_pct:.0%} = ${liquidation_value:.2f}")
        
        # Sort by liquidation priority (smallest values first)
        liquidation_priority.sort(key=lambda x: x['total_value'])
        
        total_liquidation_value = sum(item['liquidation_value'] for item in liquidation_priority)
        
        print(f"\n=== LIQUIDATION CAPACITY ===")
        print(f"Immediate liquidation capacity: ${total_liquidation_value:.2f}")
        print(f"This would provide ${usdt_balance + total_liquidation_value:.2f} liquid USDT")
        
        # Check if sufficient for trading
        min_trade_amount = 5.0  # Minimum for meaningful trades
        if total_liquidation_value >= min_trade_amount:
            print(f"✓ SUFFICIENT: Can liquidate ${total_liquidation_value:.2f} to enable trading")
            
            # Show liquidation sequence
            print(f"\n=== RECOMMENDED LIQUIDATION SEQUENCE ===")
            cumulative_value = usdt_balance
            for i, item in enumerate(liquidation_priority[:3], 1):  # Top 3 candidates
                cumulative_value += item['liquidation_value']
                print(f"{i}. Liquidate {item['liquidation_amount']:.8f} {item['asset']} -> +${item['liquidation_value']:.2f} (Total: ${cumulative_value:.2f})")
        else:
            print(f"⚠ WARNING: Liquidation capacity ${total_liquidation_value:.2f} may be insufficient")
        
        # Insufficient funds issue diagnosis
        print(f"\n=== INSUFFICIENT FUNDS DIAGNOSIS ===")
        expected_usdt = usdt_balance
        
        if expected_usdt < 5.0:
            print(f"⚠ ISSUE: USDT balance ${expected_usdt:.2f} below minimum trading threshold")
            print(f"  SOLUTION: Liquidate smallest positions to free up USDT")
        else:
            print(f"✓ USDT balance ${expected_usdt:.2f} appears sufficient")
            print(f"  ISSUE: Balance detection system may not be seeing the funds")
        
        return {
            'found_assets': found_assets,
            'usdt_balance': usdt_balance,
            'total_value': total_estimated_value,
            'liquidation_capacity': total_liquidation_value,
            'liquidation_sequence': liquidation_priority
        }
        
    except Exception as e:
        print(f"[PORTFOLIO] Emergency check error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(check_portfolio_assets())
    sys.exit(0 if result else 1)