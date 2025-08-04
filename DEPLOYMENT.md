# 🚀 PRODUCTION DEPLOYMENT GUIDE - 2025

## 🔒 SECURITY FIRST - API Configuration

### ⚠️ CRITICAL: API Key Security Checklist

**BEFORE DEPLOYMENT, VERIFY:**

- [ ] **API Key Permissions**: ONLY `Query Funds`, `Query Orders`, `Create Orders`
- [ ] **NO WITHDRAWAL ACCESS**: Verify withdrawal permissions are DISABLED
- [ ] **IP Whitelisting**: Restrict API access to your server IP only
- [ ] **2FA Enabled**: Two-factor authentication active on Kraken account
- [ ] **Secure Storage**: API credentials stored in encrypted .env file
- [ ] **Key Rotation**: Plan monthly API key rotation schedule

### 🛡️ Production API Configuration

```bash
# Create secure .env file
cp .env.example .env
chmod 600 .env  # Restrict file permissions

# Configure with minimal permissions
KRAKEN_API_KEY=your_read_only_api_key
KRAKEN_API_SECRET=your_api_secret_no_withdrawal
KRAKEN_API_TIER=pro
```

## 🧪 PRE-DEPLOYMENT TESTING

### Phase 1: Forward Testing (24-48 Hours)

```bash
# Create test configuration
cp config.json config_test.json

# Edit config_test.json to set minimal position sizes:
# "position_size_usdt": 5.0
# "max_position_size_usdt": 10.0
# "paper_trading": true

# Run bot with test config
python scripts/live_launch.py --config config_test.json

# Or use the dedicated test script
python scripts/test_bot_startup.py
```

### Phase 2: Performance Validation

**Monitor These Metrics:**
- Trade execution success rate (>95%)
- API error rate (<1%)
- Memory usage stability
- Decimal precision accuracy
- Stop-loss execution timing

### Phase 3: Security Testing

```bash
# Test API failure scenarios
# Temporarily disable API access and verify bot handles gracefully

# Test with invalid nonce
# Verify bot recovers from nonce errors

# Test rate limiting
# Ensure circuit breaker activates properly
```

## 🖥️ PRODUCTION INFRASTRUCTURE

### Server Requirements

**Minimum Specs:**
- 2 CPU cores, 4GB RAM
- 20GB SSD storage
- Ubuntu 20.04+ or equivalent
- Stable internet (99.9% uptime)

**Recommended Cloud Providers:**
- AWS EC2 t3.small or larger
- DigitalOcean Droplet $20/month plan
- Google Cloud e2-standard-2

### Production Setup Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

echo "🚀 Deploying Crypto Trading Bot to Production..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.8+
sudo apt install python3.8 python3-pip python3-venv -y

# Create production user
sudo useradd -m -s /bin/bash tradingbot
sudo usermod -aG sudo tradingbot

# Clone repository
cd /home/tradingbot
git clone https://github.com/your-username/crypto-trading-bot-2025.git crypto-bot
cd crypto-bot

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
chmod 600 .env
nano .env  # Configure API keys

# Test installation
python3 -c "from src.bot import KrakenTradingBot; print('✅ Bot import successful')"

# Test all critical imports
python3 scripts/test_imports.py

# Test API connectivity
python3 scripts/test_kraken_connection.py

echo "✅ Production deployment complete!"
echo "⚠️  CONFIGURE .env FILE BEFORE STARTING"
```

## 📊 MONITORING & ALERTING

### Real-Time Monitoring Setup

```python
# healthcheck.py - Continuous bot monitoring
import time
import smtplib
from email.mime.text import MIMEText

def check_bot_health():
    """Monitor bot health and send alerts"""
    
    # Check if bot process is running
    if not is_bot_running():
        send_alert("🚨 CRITICAL: Trading bot stopped!")
    
    # Check recent trade activity
    if no_trades_last_hour():
        send_alert("⚠️ WARNING: No trades in last hour")
    
    # Check API connectivity
    if api_errors_high():
        send_alert("🔥 ALERT: High API error rate")
    
    # Check balance changes
    if unexpected_balance_drop():
        send_alert("💰 CRITICAL: Unexpected balance decrease")

def send_alert(message):
    """Send email/SMS alert"""
    # Configure your notification method
    print(f"ALERT: {message}")

if __name__ == "__main__":
    while True:
        check_bot_health()
        time.sleep(300)  # Check every 5 minutes
```

### Log Management

```bash
# Set up log rotation
sudo nano /etc/logrotate.d/tradingbot

# Add this configuration:
/home/tradingbot/crypto-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## 🔄 DEPLOYMENT CHECKLIST

### Pre-Launch Verification

- [ ] **Bot Passes All Tests**: Forward testing successful for 24+ hours
- [ ] **API Security Verified**: No withdrawal permissions, IP whitelisted
- [ ] **Monitoring Active**: Health checks and alerting configured
- [ ] **Backups Configured**: Database and config files backed up
- [ ] **Emergency Procedures**: Stop procedures documented and tested
- [ ] **Performance Baselines**: Expected trade frequency and profit targets set

### Launch Sequence

1. **Start with Minimal Risk**
   ```bash
   # Begin with smallest position sizes
   python3 scripts/live_launch.py --config config_test.json
   
   # Or use paper trading mode first
   python3 scripts/live_launch.py --paper-trading
   ```

2. **Monitor First 24 Hours**
   - Check every 2 hours for first day
   - Verify all trades execute correctly
   - Monitor for any errors or issues

3. **Gradual Scale-Up**
   - Week 1: $5-10 position sizes
   - Week 2: $10-20 position sizes (if performance good)
   - Month 1+: Full position sizes as configured

### Emergency Procedures

**If Something Goes Wrong:**

```bash
# Emergency stop
pkill -f "live_launch.py"
pkill -f "python.*main.py"

# Check current positions
python3 scripts/check_portfolio_status.py

# Force close positions if needed
python3 scripts/emergency_sell.py

# Check bot status
python3 scripts/check_bot_status.py
```

## 📈 POST-DEPLOYMENT OPTIMIZATION

### Performance Review Schedule

**Daily (First Week):**
- Trade execution review
- Error log analysis
- Performance metrics check

**Weekly:**
- Profit/loss analysis
- Strategy effectiveness review
- System resource usage

**Monthly:**
- Full system audit
- API key rotation
- Strategy parameter optimization

### Success Metrics

**Target KPIs:**
- Trade success rate: >90%
- Daily profit target: 0.5-2%
- Maximum drawdown: <5%
- API error rate: <0.1%
- System uptime: >99.5%

## ⚠️ RISK MANAGEMENT

### Position Limits
- Never risk more than 2% of total capital per trade
- Maximum 10 concurrent positions
- Daily loss limit: 5% of account value

### Circuit Breakers
- Auto-stop if 3 consecutive losses
- API error threshold: 10 errors/hour
- Unusual balance change detection

### Emergency Contacts
- Primary: [Your Phone]
- Secondary: [Backup Contact]
- Exchange Support: [Kraken Support]

---

## 🎯 SUCCESS CRITERIA

Your bot is production-ready when:

✅ All security measures implemented  
✅ 48+ hours forward testing successful  
✅ Monitoring and alerting active  
✅ Emergency procedures tested  
✅ Performance meets target metrics  

**Remember: Start small, monitor closely, scale gradually!**