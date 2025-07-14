# Claude Code Tools for Trading Bot Development

This document provides instructions for using Claude Code CLI to improve and maintain your trading bot. These tools will help you fix errors, improve stability, and lock down working components.

## Setup Instructions

### Prerequisites

1. Windows with WSL (Windows Subsystem for Linux) installed
2. Claude Code CLI installed in WSL
3. Python 3.6+ in WSL

### Getting Started

1. Open PowerShell as Administrator
2. Navigate to the project directory:
   ```powershell
   cd C:\projects050625\projects\active\tool-crypto-trading-bot-2025
   ```
3. Make scripts executable (one-time setup):
   ```powershell
   .\make_scripts_executable.ps1
   ```

## Available Tools

### 1. Claude Code Assistant

The `run_claude_assistant.ps1` script provides a menu-driven interface for using Claude Code:

```powershell
.\run_claude_assistant.ps1
```

Options:

- Run the trading system completion tool
- Start Claude Code in interactive mode
- Run a specific Claude Code command
- Check trading bot status

### 2. Trading Bot Fixes

The `use_claude_prompt.ps1` script focuses specifically on fixing the trading bot issues:

```powershell
.\use_claude_prompt.ps1
```

Options:

- Run Claude Code with the trading bot fixes prompt
- Start Claude Code in interactive mode
- Run Claude Code with specific file analysis

### 3. Stable File Locker

The `lock_stable_files.py` script helps you identify and lock down files that are working correctly:

```powershell
C:\Windows\System32\wsl.exe -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && python lock_stable_files.py"
```

Features:

- Mark files as stable with version information
- Check for modifications to stable files
- Generate stability reports
- Command-line and interactive modes

## Common Tasks

### Fix Exchange Connection Issues

```
C:\Windows\System32\wsl.exe -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && echo 'Analyze src/exchange/native_kraken_exchange.py and implement robust error handling with retry logic and circuit breaker pattern' | claude"
```

### Improve Health Monitoring

```
C:\Windows\System32\wsl.exe -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && echo 'Enhance the health monitoring system to provide better diagnostics and recovery capabilities' | claude"
```

### Fix Strategy Timeout Issues

```
C:\Windows\System32\wsl.exe -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && echo 'Fix strategy timeout issues by implementing asynchronous execution and proper timeout handling' | claude"
```

## For Linux/WSL Users

If you prefer working directly in WSL, you can use the bash script versions:

```bash
./use_claude_prompt.sh
```

Or run Claude Code directly:

```bash
claude
```

## Troubleshooting

If you encounter issues:

1. Ensure WSL is properly installed and configured
2. Verify Claude Code CLI is installed in WSL
3. Check that scripts have executable permissions in WSL
4. Run the scripts from the project root directory

For WSL-specific issues, consult the WSL documentation.

## Additional Resources

- Claude Code CLI documentation: https://docs.anthropic.com/claude/docs/claude-code-cli
- Trading bot documentation: See the `docs/` directory
- WSL documentation: https://learn.microsoft.com/en-us/windows/wsl/
