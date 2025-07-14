#!/usr/bin/env python3
"""
Diagnostic script to test balance checking issue
"""

import asyncio
import logging
from decimal import Decimal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_balance_flow():
    """Test the balance checking flow with mock data"""
    
    # Simulate the balance manager data structure from logs
    mock_balances = {
        'ALGO': 113.40765552,
        'ATOM': 8.00000000,
        'AVAX': 4.10261672,
        'BERA': 5.00951000,
        'AI16Z': 189.47397,
        'SOL': 0.0003481892,
        'USDT': 1.33117415
    }
    
    # Test the get_balance logic
    asset = 'ALGO'
    balance_data = mock_balances.get(asset)
    
    print(f"Testing balance retrieval for {asset}")
    print(f"Raw balance data: {balance_data} (type: {type(balance_data)})")
    
    # Convert to dict format (simulating get_balance)
    if isinstance(balance_data, (int, float, str)):
        amount = float(balance_data)
        result = {'free': amount, 'used': 0, 'total': amount}
        print(f"Converted to dict: {result}")
    
    # Simulate get_balance_for_asset
    if isinstance(result, dict):
        free_balance = float(result.get('free', 0))
        print(f"Dict balance, free: {free_balance}")
        if free_balance > 0:
            print(f"✓ Balance check would return: {free_balance}")
        else:
            print(f"✗ Balance check would return 0")
    
    # Test the execution logic
    print("\n--- Testing execution logic ---")
    base_asset = 'ALGO'
    asset_balance = 0
    
    # This is what should happen in the code
    asset_variants = [base_asset]  # Simplified
    
    for variant in asset_variants:
        # Simulate get_balance_for_asset call
        balance_result = free_balance  # From above
        
        if isinstance(balance_result, (int, float)):
            asset_balance = float(balance_result)
        
        print(f"Trying {variant} balance for {base_asset}: {asset_balance:.8f}")
        
        if asset_balance > 0:
            print(f"Found {base_asset} balance using variant {variant}: {asset_balance:.8f}")
            break
    
    if asset_balance <= 0:
        print(f"ERROR: No {base_asset} balance to sell")
    else:
        print(f"SUCCESS: Can sell {asset_balance:.8f} {base_asset}")

if __name__ == "__main__":
    asyncio.run(test_balance_flow())