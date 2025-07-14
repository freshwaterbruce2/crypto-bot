Apply the Kraken minimum order learning fix.
File: src/enhanced_trade_executor_with_assistants.py  
Integration point: Around the buy order section (search for "if side.lower() == 'buy'")
Use portfolio_intelligence.validate_trade_minimums() to check learned minimums.
Adjust crypto_amount and position_size based on validation results.
Quick fix only - no deep analysis.