# Kraken Trading Bot

Automated cryptocurrency trading bot for Kraken exchange using fee-free micro-scalping strategies.

## Setup

1. **Create .env file** with your Kraken API credentials:
   ```
   KRAKEN_API_KEY=your_api_key_here
   KRAKEN_API_SECRET=your_api_secret_here
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the bot**:
   ```bash
   python scripts/live_launch.py
   ```

## Strategy

The bot uses a fee-free micro-scalping strategy targeting 0.5% profits per trade with tight stop losses. It monitors multiple USDT pairs for optimal entry/exit points.

## Requirements

- Python 3.9+
- Windows 10/11
- Kraken API credentials with trading permissions
- Minimum 5GB free disk space
