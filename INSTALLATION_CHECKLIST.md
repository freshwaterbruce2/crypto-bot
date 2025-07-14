# Claude Code Installation Checklist

## Current Status
- [ ] WSL is NOT installed (wsl command not recognized)
- [ ] Need to enable Windows features first
- [ ] Scripts created in project directory

## Installation Steps Order

### 1. Enable WSL (DO THIS FIRST!)
Run ONE of these as Administrator:
- Option A: Run `enable_wsl_proper.ps1` in PowerShell as Admin
- Option B: Run `enable_wsl.bat` as Administrator

### 2. RESTART YOUR COMPUTER
This is mandatory after enabling WSL features!

### 3. Install Ubuntu (After Restart)
Open PowerShell as Administrator and run:
```
wsl --install -d Ubuntu
```

### 4. Set up Ubuntu
- Open Ubuntu from Start Menu
- Create username and password
- Wait for initial setup to complete

### 5. Install Claude Code
In Ubuntu terminal:
```bash
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/
bash setup_claude_ubuntu.sh
```

### 6. Authenticate
```bash
claude auth
```

## Files Created
- `enable_wsl.bat` - Batch script to enable WSL
- `enable_wsl_proper.ps1` - PowerShell script to enable WSL (recommended)
- `install_claude_code.ps1` - Original installation attempt
- `setup_claude_ubuntu.sh` - Ubuntu setup script for Claude Code
- `CLAUDE_CODE_SETUP_GUIDE.md` - Comprehensive guide

## Quick Commands Reference
```bash
# After everything is installed:
claude                    # Start Claude Code
claude "write a function" # Quick command
claude auth              # Re-authenticate
claude logout            # Logout
```

## For Trading Bot Development
```bash
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/
claude "create a grid trading strategy in Python"
```
