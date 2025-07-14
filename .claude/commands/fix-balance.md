Fix the insufficient funds error in src/enhanced_trade_executor_with_assistants.py.
Focus ONLY on the balance checking section around line 257.
The fix should check if funds are deployed using balance_manager.get_deployment_status().
Replace the zero balance check with portfolio intelligence logic.
Do NOT analyze other parts of the file.
Target: Allow trading when USDT is low but capital is deployed in other assets.