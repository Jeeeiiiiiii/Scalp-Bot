# ⚡ Quick Start Guide

**For experienced users who want to start immediately**

---

## 🚀 5-Minute Setup (Paper Trading)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Binance API Keys
- Go to: https://www.binance.com/en/my/settings/api-management
- Create new API key
- Enable: Reading + Spot Trading
- Disable: Withdrawals + Futures
- Copy API key and secret

### 3. Configure Bot
Edit `config_live.json`:
```json
{
  "exchange": {
    "api_key": "paste_your_api_key_here",
    "api_secret": "paste_your_secret_here"
  },
  "bot_settings": {
    "paper_trading": true,  ← Keep TRUE for testing!
    "initial_balance": 18   ← Your USDT amount
  },
  "risk_management": {
    "max_position_size_usd": 18  ← Match your balance
  }
}
```

### 4. Run Paper Trading
```bash
python range_fvg_bot_micro.py
```

Expected output:
```
🎮 PAPER TRADING MODE (Simulated)
✅ Connected to Binance
💰 Balance: $18.00 USDT (paper)
📊 Watching BTC/USDT...
```

---

## 💰 Go Live (After Testing)

### 1. Change One Setting
Edit `config_live.json`:
```json
"paper_trading": false  ← Changed from true
```

### 2. Run Live
```bash
python range_fvg_bot_micro.py
```

Expected output:
```
🔴 LIVE TRADING MODE - REAL MONEY!
⚠️  YOU CAN LOSE MONEY - Proceed? (yes/no): yes
✅ Connected to Binance
💰 Real balance: $18.50 USDT
📊 Watching BTC/USDT...
```

---

## 📋 Common Commands

### Start Bot
```bash
python range_fvg_bot_micro.py
```

### Stop Bot
```
Press Ctrl+C
```

### Run Backtest (Test strategy on past data)
```bash
# Original v1.0
python range_fvg_backtest.py

# Enhanced v2.0
python range_fvg_backtest_v2.py

# Ultra-Selective v2.1 (recommended)
python range_fvg_backtest_v2_1.py
```

### Check Binance Balance
```bash
# Windows
python -c "import ccxt; ex = ccxt.binance({'apiKey': 'YOUR_KEY', 'secret': 'YOUR_SECRET'}); print(f\"Balance: ${ex.fetch_balance()['USDT']['free']:.2f} USDT\")"

# Mac/Linux
python -c 'import ccxt; ex = ccxt.binance({"apiKey": "YOUR_KEY", "secret": "YOUR_SECRET"}); print(f"Balance: ${ex.fetch_balance()[\"USDT\"][\"free\"]:.2f} USDT")'
```

### Save Logs to File
```bash
python range_fvg_bot_micro.py > bot_logs.txt 2>&1
```

### Run in Background (Mac/Linux)
```bash
nohup python range_fvg_bot_micro.py > bot_logs.txt 2>&1 &
```

### Check if Bot is Running
```bash
# Windows
tasklist | findstr python

# Mac/Linux
ps aux | grep range_fvg_bot_micro
```

---

## ⚙️ Quick Config Changes

### Trade More Per Day
```json
"max_daily_trades": 2  ← Change from 1 to 2
```

### Increase Risk (Higher profit, higher loss)
```json
"risk_per_trade": 0.02  ← Change from 0.015 (1.5%) to 0.02 (2%)
```

### Trade 3-Star Setups (Less selective)
Edit `range_fvg_bot_micro.py` line ~350:
```python
if setup_quality >= 3:  # Changed from 4 to 3
```

### Change Trading Pair
```json
"symbol": "ETH/USDT"  ← Trade Ethereum instead of Bitcoin
```

---

## 📊 Expected Performance

### With 1,000 Pesos (~18 USDT)
- **Profit per win:** ~30 pesos
- **Loss per trade:** ~18 pesos (max)
- **Trades/week:** 0-2
- **Trades/month:** 4-8
- **Monthly profit:** 90-150 pesos (75-85% win rate)

### With 5,000 Pesos (~95 USDT)
- **Profit per win:** ~168 pesos
- **Loss per trade:** ~90 pesos (max)
- **Trades/week:** 0-2
- **Trades/month:** 4-8
- **Monthly profit:** 500-800 pesos (75-85% win rate)

---

## 🛡️ Safety Features (Built-in)

- ✅ Automatic stop loss on every trade (1.5-1.8% max loss)
- ✅ Daily loss limit ($2 / ~125 pesos max per day)
- ✅ Max trades per day (1 by default)
- ✅ Quality filter (only 4-5 star setups)
- ✅ Position size limit (can't trade more than balance)

---

## 🚨 Troubleshooting

### "API key invalid"
→ Check API key copied correctly, enable "Spot Trading" permission

### "Insufficient balance"
→ Make sure USDT is in Spot wallet (not P2P), balance > $10

### "Bot doesn't trade"
→ Normal! Bot only trades 4-5 star setups (very selective)

### "Trade lost money"
→ Normal! Stop loss hit. Expected 15-25% of trades to lose.

### "Bot crashed"
→ Check internet, restart bot. Share error message if persists.

---

## 📞 Getting Help

### Documentation
- **Full Guide:** `PRODUCTION_DEPLOYMENT.md` (comprehensive)
- **Safety Check:** `PRE_FLIGHT_CHECKLIST.md` (before going live)
- **Strategy Details:** `README_RANGE_FVG.md` (how it works)
- **Version Comparison:** `VERSION_COMPARISON.md` (v1 vs v2 vs v2.1)

### Support
- **Binance:** https://www.binance.com/en/support (24/7 live chat)
- **Bot Issues:** Share error message with developer

---

## 🎯 Quick Reference

| Action | Command |
|--------|---------|
| **Start bot** | `python range_fvg_bot_micro.py` |
| **Stop bot** | Press `Ctrl+C` |
| **Run backtest** | `python range_fvg_backtest_v2_1.py` |
| **Check balance** | Log in to Binance app/website |
| **View logs** | Check terminal output or `logs/trading_bot.log` |
| **Emergency stop** | `Ctrl+C` then close positions on Binance |

---

## ⏰ Trading Schedule

**All times in EST (Eastern Standard Time)**

| Time (EST) | Time (Manila) | Action |
|------------|---------------|--------|
| **9:30 AM** | 10:30 PM | Range marked (15m candle) |
| **9:45 AM** | 10:45 PM | Range complete, start watching for FVG |
| **10:00 AM - 12:00 PM** | 11:00 PM - 1:00 AM | Trading window |
| **12:00 PM** | 1:00 AM | Entry cutoff (no new trades after) |

**Bot must be running before 9:30 AM EST to trade that day!**

---

## ✅ Daily Routine

### Morning (Before 9:30 AM EST / 10:30 PM Manila)
1. Check bot is running
2. Verify internet connection
3. Check Binance balance

### Evening (After 12 PM EST / 1 AM Manila)
1. Check if bot traded today
2. Review P&L if trade occurred
3. Check balance
4. Let bot keep running for next day

### Weekly
1. Calculate total trades
2. Calculate win rate
3. Calculate total P&L
4. Decide if any adjustments needed

---

## 🔄 Version Selection

**Which bot file to run?**

| File | Use Case | Win Rate | Trades/Week |
|------|----------|----------|-------------|
| `range_fvg_bot.py` | Standard capital ($100+) | 50-60% | 2-4 |
| `range_fvg_bot_micro.py` | **Small capital ($18-95)** | **75-85%** | **0-2** |
| `range_fvg_bot_live.py` | Advanced users | Configurable | Configurable |

**For 1,000-5,000 pesos: Use `range_fvg_bot_micro.py`** ✅

---

## 🎓 Pro Tips

1. **Don't panic if bot doesn't trade**
   - Selective by design
   - Some weeks = 0 trades (normal!)
   - Quality > quantity

2. **Trust the stop loss**
   - Automatic protection
   - Max loss per trade: 1.5-1.8%
   - Better to take small loss than big loss

3. **Review skipped setups**
   - Bot logs why setups were skipped
   - Learn to recognize low-quality setups
   - Understand the strategy better

4. **Start small, grow gradually**
   - Prove profitability first
   - Then add more capital
   - Compound your gains

5. **Track your performance**
   - Keep spreadsheet of trades
   - Calculate actual win rate
   - Compare to expected (75-85%)

---

## 📈 Growth Path

### Week 1: Testing Phase
- Paper trade 1-3 days
- Verify bot behavior
- Zero risk

### Week 2-4: Live with Minimal Capital
- Start with 1,000 pesos
- Monitor closely
- Learn the system

### Month 2: Evaluate & Scale
- If profitable → Add 1,000-2,000 pesos
- If unprofitable → Review and adjust
- Track metrics carefully

### Month 3+: Compound
- Reinvest profits
- Grow capital gradually
- Maintain discipline

---

## 🎯 Success Metrics

**Bot is working well if:**
- ✅ Win rate 70%+ over 10+ trades
- ✅ Profit factor 2.5+
- ✅ No emotional trading (bot runs automatically)
- ✅ Consistent monthly profit
- ✅ Growing account balance

**Red flags:**
- ❌ Win rate < 60% over 10+ trades
- ❌ Frequent unexpected losses
- ❌ Bot crashes often
- ❌ Not following risk limits

---

## 🔐 Security Reminders

- ✅ Never share API keys
- ✅ Enable 2FA on Binance
- ✅ Disable withdrawal permission on API
- ✅ Use strong password
- ✅ Log out of Binance on public computers
- ✅ Save backup of API keys securely

---

**Ready to start?** → Follow the 5-minute setup above! 🚀

**Need more details?** → Read `PRODUCTION_DEPLOYMENT.md`

**Want safety check?** → Review `PRE_FLIGHT_CHECKLIST.md`

---

**Last updated:** 2025-11-17
**Bot version:** Micro Capital v1.0
**Status:** Production Ready ✅
