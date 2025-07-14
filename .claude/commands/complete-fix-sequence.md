# COMPLETE BOT FIX SEQUENCE

Execute these commands in order to fix all issues:

1. Apply WebSocket callback fix:
   /fix-websocket-callbacks

2. Apply initialization order fix:
   /fix-init-order

3. Apply signal execution fix:
   /fix-signal-execution

4. Update WebSocket manager for Kraken v2:
   - File: src/websocket_manager.py
   - Change URLs to: wss://ws.kraken.com/v2
   - Update message format to v2 structure

5. Add self-diagnostic system:
   - Create: src/learning/self_diagnostic_system.py
   - Import in bot.py
   - Start diagnostics task in start()

6. Update config.json:
   - Set quote_currency: "USDT"
   - Set position_size: 10.0
   - Set min_position_size: 5.0
   - Remove any non-USDT pairs

7. Clean up project:
   - Delete all kraken_compliance_*.py except one
   - Delete old strategy files
   - Delete test/backup files

8. Test the bot:
   python scripts/simple_bot_launcher.py

All trades will use USDT only.
Minimum trade size: $5 USDT.
Target: 0.5% profits per trade.