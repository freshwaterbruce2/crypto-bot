# CLEAN UP PROJECT STRUCTURE

Execute these cleanup tasks to remove redundant files and organize the project:

## 1. DELETE REDUNDANT KRAKEN COMPLIANCE FILES

Find and delete all duplicate kraken_compliance files, keeping only one:
```bash
# List all kraken_compliance files
find src -name "kraken_compliance*.py" -type f

# Delete all except the main one
rm -f src/kraken_compliance_2.py
rm -f src/kraken_compliance_3.py
rm -f src/kraken_compliance_checker.py
rm -f src/kraken_compliance_validator.py
# Keep only: src/kraken_compliance.py
```

## 2. REMOVE OLD/UNUSED FILES

Delete these unnecessary files:
```bash
# Remove old initialization files
rm -f src/initialization_recovery_system.py
rm -f src/initialization_validator.py

# Remove test and backup files
rm -rf src/test_*
rm -rf src/backup_*
rm -f src/*_old.py
rm -f src/*_backup.py

# Remove non-USDT strategy files
rm -f src/strategies/*_btc.py
rm -f src/strategies/*_eth.py
# Keep only strategies that work with USDT pairs
```

## 3. CLEAN CACHE AND TEMP FILES

```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove log files older than 7 days
find logs -name "*.log" -type f -mtime +7 -delete

# Remove empty directories
find src -type d -empty -delete
```

## 4. ORGANIZE REMAINING FILES

Ensure proper structure:
```
src/
├── bot.py                    # Main bot file
├── config.json              # Configuration
├── websocket_manager.py     # WebSocket v2 handler
├── enhanced_trade_executor_with_assistants.py
├── kraken_compliance.py     # Single compliance file
├── assistants/              # Assistant managers
├── learning/                # Learning systems
│   └── self_diagnostic_system.py
├── strategies/              # USDT-only strategies
├── utils/                   # Utilities
└── components/              # Core components
```

## 5. VERIFY CLEANUP

After cleanup, verify:
```bash
# Count Python files
echo "Total Python files: $(find src -name "*.py" | wc -l)"

# Check for duplicates
echo "Checking for duplicate functionality..."
grep -r "class KrakenCompliance" src/
grep -r "class InitializationRecovery" src/
grep -r "class WebSocketManager" src/

# List remaining files
tree src -I "__pycache__"
```

## 6. UPDATE IMPORTS

After deleting files, update any broken imports:
```bash
# Find all imports of deleted files
grep -r "from.*kraken_compliance_" src/
grep -r "import.*initialization_recovery" src/

# Update them to use the consolidated files
```

Execute all cleanup commands to streamline the project.