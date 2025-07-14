# GitHub Authentication Setup

## Option 1: Use Personal Access Token (Recommended)

1. **Generate Personal Access Token:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full repository access)
   - Copy the token (save it securely)

2. **Configure Git with Token:**
   ```bash
   git remote set-url origin https://freshwaterbruce2:YOUR_TOKEN@github.com/freshwaterbruce2/crypto-bot.git
   ```

3. **Push to GitHub:**
   ```bash
   git push -u origin main
   ```

## Option 2: Use GitHub CLI (Alternative)

1. **Install GitHub CLI:**
   ```bash
   sudo apt install gh
   ```

2. **Authenticate:**
   ```bash
   gh auth login
   ```

3. **Push:**
   ```bash
   git push -u origin main
   ```

## Current Status

- ✅ Repository initialized with 560 files
- ✅ Remote added: https://github.com/freshwaterbruce2/crypto-bot.git
- ✅ Branch renamed to main
- ⏳ **Next**: Authenticate and push

## After Authentication, Run:

```bash
git push -u origin main
```

This will upload your entire crypto trading bot project to GitHub!