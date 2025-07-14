# PROJECT CLEANUP

Clean up the trading bot project by removing redundant files.

## DELETE DUPLICATE FILES

Remove all duplicate kraken_compliance files:
- Delete: src/kraken_compliance_2.py
- Delete: src/kraken_compliance_3.py  
- Delete: src/kraken_compliance_checker.py
- Keep only: src/kraken_compliance.py

Remove old initialization files:
- Delete: src/initialization_recovery_system.py
- Delete: src/initialization_validator.py

## REMOVE UNNECESSARY FILES

Delete test and backup files:
- Remove all files matching: test_*.py
- Remove all files matching: *_backup.py
- Remove all files matching: *_old.py
- Remove __pycache__ directories

Delete non-USDT files:
- Remove strategies not using USDT pairs
- Remove any BTC or ETH specific modules

## CLEAN LOGS

Remove old log files:
- Delete logs older than 7 days
- Keep only recent kraken_bot.log

## FINAL STRUCTURE

After cleanup, src/ should contain:
- bot.py (main)
- config.json
- websocket_manager.py
- enhanced_trade_executor_with_assistants.py
- kraken_compliance.py (single file)
- Directories: assistants/, learning/, strategies/, utils/, components/

Execute cleanup to streamline the project.