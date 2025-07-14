# Claude Code Installation Guide for Windows 11 with WSL

## Prerequisites
- Windows 11 (or Windows 10 version 2004 or higher)
- Administrator access
- Internet connection
- Claude Pro or Max subscription (for Claude Code access)

## Step 1: Install WSL

### Option A: Using PowerShell (Recommended)
1. Open PowerShell as Administrator
   - Right-click on Start menu
   - Select "Windows Terminal (Admin)" or "PowerShell (Admin)"

2. Run the following command:
   ```powershell
   wsl --install -d Ubuntu
   ```

3. Restart your computer when prompted

### Option B: Using the provided script
1. Navigate to: C:\projects050625\projects\active\tool-crypto-trading-bot-2025\
2. Right-click on `install_claude_code.ps1`
3. Select "Run with PowerShell" as Administrator

## Step 2: Set up Ubuntu

After restart:
1. Open "Ubuntu" from the Start Menu
2. Wait for installation to complete (may take a few minutes)
3. Create a username and password when prompted
   - This will be your Linux username (all lowercase, no spaces)
   - Password won't show while typing (this is normal)

## Step 3: Install Claude Code in Ubuntu

### Option A: Manual Installation
Run these commands in Ubuntu terminal one by one:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version

# Install Claude Code
sudo npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth
```

### Option B: Using the setup script
1. In Ubuntu terminal, run:
   ```bash
   cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/
   bash setup_claude_ubuntu.sh
   ```

## Step 4: Authenticate Claude Code

1. Run: `claude auth`
2. Follow the prompts:
   - It will open a browser window
   - Log in with your Claude.ai account
   - Authorize the application
   - Return to terminal

## Step 5: Test Claude Code

1. In Ubuntu terminal, run:
   ```bash
   claude
   ```

2. You should see the Claude Code interactive prompt

## Using Claude Code for Trading Bot Development

### Navigate to your project
```bash
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/
```

### Example commands:
- `claude "create a python script for grid trading"`
- `claude "analyze this trading strategy"`
- `claude "optimize this code for performance"`

### VS Code Integration
1. Install VS Code if not already installed
2. In Ubuntu terminal, navigate to project and run:
   ```bash
   code .
   ```
3. VS Code will open with WSL integration
4. Claude Code extension will be installed automatically

## Troubleshooting

### WSL not found
- Ensure Windows is updated
- Enable virtualization in BIOS
- Run: `dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart`

### Permission denied errors
- Always use `sudo` for npm global installs
- Check file permissions: `ls -la`

### Claude auth issues
- Ensure you have a Claude Pro or Max subscription
- Try logging out and back in: `claude logout` then `claude auth`

### Node.js issues
- If Node.js doesn't install, try using nvm instead:
  ```bash
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
  source ~/.bashrc
  nvm install 20
  nvm use 20
  ```

## Memory Server Integration
After setup, remember to:
1. Update memory server with installation status
2. Document any custom configurations
3. Note the WSL Ubuntu path: /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/
