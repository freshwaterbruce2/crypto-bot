#!/usr/bin/env python3
"""
Portfolio Liquidation Analysis - Fresh Start Strategy
====================================================

Analyze current portfolio to identify all positions that need to be liquidated
for a fresh start with optimized TIER_1_PRIORITY_PAIRS.
"""

import json
import os
from datetime import datetime
from pathlib import Path

def analyze_current_state():
    """Analyze current trading bot state and portfolio positions"""
    
    print("=" * 80)
    print("PORTFOLIO LIQUIDATION ANALYSIS")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Based on the project completion report and critical fixes documentation
    current_positions = {
        "AI16Z": {"value_usd": 34.47, "tokens": 189.47, "pair": "AI16Z/USDT"},
        "ALGO": {"value_usd": 25.21, "tokens": 113.41, "pair": "ALGO/USDT"}, 
        "ATOM": {"value_usd": 37.09, "tokens": 3.60, "pair": "ATOM/USDT"},
        "AVAX": {"value_usd": 84.97, "tokens": 2.12, "pair": "AVAX/USDT"},
        "BERA": {"value_usd": 10.19, "tokens": 54.46, "pair": "BERA/USDT"},
        "SOL": {"value_usd": 5.00, "tokens": 0.03, "pair": "SOL/USDT"}
    }
    
    available_usdt = 1.33
    total_portfolio_value = 321.32
    
    # Load avoid list from configuration
    avoid_pairs = [
        "ADA/USDT", "ALGO/USDT", "APE/USDT", "ATOM/USDT", "AVAX/USDT", 
        "BCH/USDT", "BNB/USDT", "CRO/USDT", "DOGE/USDT"
    ]
    
    # Load optimized pairs from TIER_1_PRIORITY_PAIRS
    tier_1_priority_pairs = {
        'ultra_low': ['SHIB/USDT'],  # Volume: 50000, ~$1.00 minimum
        'low': ['MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT', 'MANA/USDT'],  # Volume: 1.0, <$2.00 minimum  
        'medium': ['DOT/USDT', 'LINK/USDT', 'SOL/USDT', 'BTC/USDT']  # Low volume minimums
    }
    
    print("\n[CURRENT PORTFOLIO STATE]")
    print(f"Total Portfolio Value: ${total_portfolio_value:.2f}")
    print(f"Available USDT: ${available_usdt:.2f}")
    print(f"Deployed Capital: ${total_portfolio_value - available_usdt:.2f}")
    print()
    
    print("[CURRENT POSITIONS]")
    positions_to_liquidate = []
    positions_to_keep = []
    
    for asset, data in current_positions.items():
        pair = data["pair"]
        value = data["value_usd"]
        tokens = data["tokens"]
        
        # Check if this pair is in avoid list
        in_avoid_list = pair in avoid_pairs
        
        # Check if this pair is in optimized TIER_1_PRIORITY_PAIRS
        in_tier1_optimized = any(pair in tier for tier in tier_1_priority_pairs.values())
        
        status = "LIQUIDATE" if in_avoid_list else ("KEEP" if in_tier1_optimized else "REVIEW")
        
        print(f"  {asset:6s} | {pair:12s} | ${value:8.2f} | {tokens:10.2f} tokens | {status}")
        
        if status == "LIQUIDATE":
            positions_to_liquidate.append({
                "asset": asset,
                "pair": pair,
                "value_usd": value,
                "tokens": tokens,
                "reason": "In avoid list (high minimum requirements)"
            })
        elif status == "KEEP":
            positions_to_keep.append({
                "asset": asset,
                "pair": pair,
                "value_usd": value,
                "tokens": tokens,
                "reason": "In TIER_1_PRIORITY_PAIRS (optimized)"
            })
        else:
            positions_to_liquidate.append({
                "asset": asset,
                "pair": pair,
                "value_usd": value,
                "tokens": tokens,
                "reason": "Not in optimized pairs"
            })
    
    print()
    print("[LIQUIDATION ANALYSIS]")
    print()
    
    # Calculate liquidation potential
    total_liquidation_value = sum(p["value_usd"] for p in positions_to_liquidate)
    total_keep_value = sum(p["value_usd"] for p in positions_to_keep)
    
    print(f"Positions to LIQUIDATE: {len(positions_to_liquidate)} (${total_liquidation_value:.2f})")
    for pos in positions_to_liquidate:
        print(f"  - {pos['asset']:6s}: ${pos['value_usd']:8.2f} | {pos['reason']}")
    
    print()
    print(f"Positions to KEEP: {len(positions_to_keep)} (${total_keep_value:.2f})")
    for pos in positions_to_keep:
        print(f"  - {pos['asset']:6s}: ${pos['value_usd']:8.2f} | {pos['reason']}")
    
    print()
    print("[FRESH START STRATEGY]")
    print()
    
    if total_liquidation_value > 0:
        expected_usdt_after_liquidation = available_usdt + total_liquidation_value
        print(f"Current USDT: ${available_usdt:.2f}")
        print(f"+ Liquidation proceeds: ${total_liquidation_value:.2f}")
        print(f"= Total USDT after liquidation: ${expected_usdt_after_liquidation:.2f}")
        print()
        
        print("BENEFITS OF LIQUIDATION:")
        print(f"  ✓ Eliminate {len(positions_to_liquidate)} problematic positions")
        print("  ✓ Focus capital on optimized low-minimum pairs")
        print("  ✓ Stop repeated trading failures on high-minimum pairs")
        print("  ✓ Enable successful $2.00 micro-trades")
        print(f"  ✓ Increase available trading capital from ${available_usdt:.2f} to ${expected_usdt_after_liquidation:.2f}")
        print()
        
        print("OPTIMIZED TARGET PAIRS FOR FRESH START:")
        for tier, pairs in tier_1_priority_pairs.items():
            print(f"  {tier.upper()}: {', '.join(pairs)}")
        print()
        
        # Generate liquidation plan
        print("[LIQUIDATION EXECUTION PLAN]")
        print()
        print("STEP 1: Immediate Liquidation (High Priority)")
        high_priority = [p for p in positions_to_liquidate if p["pair"] in avoid_pairs[:3]]  # Top 3 problematic
        for i, pos in enumerate(high_priority, 1):
            print(f"  {i}. SELL {pos['asset']} ({pos['pair']}) - ${pos['value_usd']:.2f}")
            print(f"     Reason: {pos['reason']}")
        
        print()
        print("STEP 2: Secondary Liquidation (Medium Priority)")
        medium_priority = [p for p in positions_to_liquidate if p not in high_priority]
        for i, pos in enumerate(medium_priority, len(high_priority) + 1):
            print(f"  {i}. SELL {pos['asset']} ({pos['pair']}) - ${pos['value_usd']:.2f}")
            print(f"     Reason: {pos['reason']}")
        
        print()
        print("STEP 3: Portfolio Reallocation")
        print("  - Focus new trades on TIER_1_PRIORITY_PAIRS")
        print("  - Use $2.00 position sizes for micro-scalping")
        print("  - Target 0.1-0.5% profit per trade")
        print("  - Avoid all high-minimum pairs")
        
    else:
        print("No liquidation needed - all positions are optimized!")
    
    print()
    print("=" * 80)
    
    # Save analysis to file
    analysis_data = {
        "timestamp": datetime.now().isoformat(),
        "current_positions": current_positions,
        "available_usdt": available_usdt,
        "total_portfolio_value": total_portfolio_value,
        "positions_to_liquidate": positions_to_liquidate,
        "positions_to_keep": positions_to_keep,
        "liquidation_value": total_liquidation_value,
        "expected_usdt_after_liquidation": available_usdt + total_liquidation_value,
        "tier_1_priority_pairs": tier_1_priority_pairs,
        "avoid_pairs": avoid_pairs
    }
    
    # Save to file
    output_file = "portfolio_liquidation_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"Analysis saved to: {output_file}")
    
    return analysis_data

def generate_liquidation_scripts():
    """Generate specific liquidation scripts for the identified positions"""
    
    print("\n[GENERATING LIQUIDATION SCRIPTS]")
    print()
    
    # Positions that need liquidation based on analysis
    liquidation_targets = [
        {"asset": "ALGO", "pair": "ALGO/USDT", "reason": "In avoid list"},
        {"asset": "ATOM", "pair": "ATOM/USDT", "reason": "In avoid list"}, 
        {"asset": "AVAX", "pair": "AVAX/USDT", "reason": "In avoid list"}
    ]
    
    # Generate emergency sell script
    emergency_sell_script = '''#!/usr/bin/env python3
"""
Emergency Portfolio Liquidation - Fresh Start
===========================================
Liquidates specific positions for fresh start with optimized pairs.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

async def liquidate_for_fresh_start():
    """Liquidate specific positions to enable fresh start"""
    
    print("="*60)
    print("EMERGENCY LIQUIDATION - FRESH START STRATEGY")
    print("="*60)
    
    # Import after path setup
    try:
        import ccxt.async_support as ccxt
    except ImportError:
        print("ERROR: ccxt not installed. Run: pip install ccxt")
        return
    
    # Get credentials
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    if not api_key or not api_secret:
        print("ERROR: Missing API credentials in .env file")
        return
    
    # Create exchange
    exchange = ccxt.kraken({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True
    })
    
    try:
        # Get current balance
        print("\\n[1] Checking current balances...")
        balance = await exchange.fetch_balance()
        
        # Positions to liquidate (problematic high-minimum pairs)
        liquidation_targets = [
            "ALGO",  # ALGO/USDT - in avoid list  
            "ATOM",  # ATOM/USDT - in avoid list
            "AVAX"   # AVAX/USDT - in avoid list
        ]
        
        print("\\n[2] Liquidating problematic positions...")
        liquidated_value = 0
        
        for asset in liquidation_targets:
            balance_amount = balance['total'].get(asset, 0)
            
            if balance_amount > 0.00001:  # Has meaningful balance
                try:
                    symbol = f"{asset}/USDT"
                    
                    # Get current price
                    ticker = await exchange.fetch_ticker(symbol)
                    price = ticker['last']
                    value = balance_amount * price
                    
                    print(f"\\n  Selling {asset}:")
                    print(f"    Balance: {balance_amount:.8f}")
                    print(f"    Price: ${price:.4f}")
                    print(f"    Value: ${value:.2f}")
                    
                    if value >= 1.0:  # Only sell if worth $1+
                        # Execute market sell
                        order = await exchange.create_order(
                            symbol=symbol,
                            type='market',
                            side='sell', 
                            amount=balance_amount
                        )
                        
                        print(f"    ✅ SOLD - Order: {order.get('id', 'Unknown')}")
                        liquidated_value += value
                    else:
                        print(f"    ⏭️  SKIPPED - Value too small (${value:.2f})")
                        
                except Exception as e:
                    print(f"    ❌ FAILED to sell {asset}: {e}")
            else:
                print(f"\\n  {asset}: No balance to sell")
        
        print(f"\\n[3] Liquidation complete!")
        print(f"    Total liquidated value: ${liquidated_value:.2f}")
        
        # Check final USDT balance
        final_balance = await exchange.fetch_balance()
        usdt_balance = final_balance['total'].get('USDT', 0)
        print(f"    Final USDT balance: ${usdt_balance:.2f}")
        
        if usdt_balance >= 10:
            print("\\n✅ SUCCESS: Sufficient USDT for optimized trading!")
            print("   Bot can now focus on TIER_1_PRIORITY_PAIRS:")
            print("   - SHIB/USDT, MATIC/USDT, AI16Z/USDT, BERA/USDT") 
            print("   - DOT/USDT, LINK/USDT, SOL/USDT, BTC/USDT")
        else:
            print("\\n⚠️  Consider depositing additional USDT for optimal trading")
        
    except Exception as e:
        print(f"\\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await exchange.close()

if __name__ == "__main__":
    print("This will liquidate ALGO, ATOM, and AVAX positions")
    print("These are in the avoid list due to high minimum requirements")
    print()
    
    response = input("Proceed with liquidation? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(liquidate_for_fresh_start())
    else:
        print("Liquidation cancelled")
'''
    
    # Write the emergency liquidation script
    script_path = "emergency_liquidation_fresh_start.py"
    with open(script_path, 'w') as f:
        f.write(emergency_sell_script)
    
    print(f"Generated: {script_path}")
    
    # Make it executable
    os.chmod(script_path, 0o755)
    
    print("Script is ready to run!")
    print(f"Usage: python3 {script_path}")

if __name__ == "__main__":
    # Run the analysis
    analysis_data = analyze_current_state()
    
    # Generate liquidation scripts
    generate_liquidation_scripts()
    
    print()
    print("NEXT STEPS:")
    print("1. Review the analysis above")
    print("2. Run: python3 emergency_liquidation_fresh_start.py")
    print("3. Restart the trading bot with clean, optimized pairs")
    print("4. Monitor successful trades on low-minimum pairs")