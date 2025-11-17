# ✅ Pre-Flight Safety Checklist

## Before Going Live - Quick Check

Print this page and check off each item before enabling real trading!

---

## 🏦 BINANCE ACCOUNT

- [ ] Binance account created
- [ ] Email/phone verified
- [ ] KYC (ID verification) completed
- [ ] 2FA (Google Authenticator) enabled
- [ ] USDT deposited via P2P
- [ ] USDT transferred to Spot wallet (not P2P wallet!)
- [ ] Balance confirmed: $____ USDT

---

## 🔑 API KEYS

- [ ] API keys generated (Profile > API Management)
- [ ] API key saved securely: `____________________`
- [ ] Secret key saved securely: `____________________`
- [ ] API permissions set correctly:
  - [ ] ✅ Enable Reading
  - [ ] ✅ Enable Spot & Margin Trading
  - [ ] ❌ Enable Withdrawals (DISABLED!)
  - [ ] ❌ Enable Futures (DISABLED!)
- [ ] IP restriction set (if applicable)

---

## ⚙️ CONFIG FILE

- [ ] Opened `config_live.json`
- [ ] API key replaced (line 10)
- [ ] Secret key replaced (line 11)
- [ ] `initial_balance` set to your USDT amount (line 23)
- [ ] `max_position_size_usd` matches your balance (line 46)
- [ ] `paper_trading` is set to `true` for testing (line 20)
- [ ] File saved

---

## 🧪 PAPER TRADING TEST

- [ ] Ran bot with paper trading: `python range_fvg_bot_micro.py`
- [ ] Bot connected successfully
- [ ] No API errors
- [ ] Bot marked range correctly
- [ ] Tested for 1-3 days
- [ ] Reviewed any simulated trades
- [ ] No crashes or errors

---

## 💰 GO LIVE CHECKLIST

- [ ] Paper trading successful
- [ ] Read PRODUCTION_DEPLOYMENT.md guide
- [ ] Understand I can lose money
- [ ] Starting with small capital (1,000-5,000 pesos)
- [ ] Know how to stop bot (Ctrl+C)
- [ ] Changed `paper_trading: false` in config (line 20)
- [ ] Saved config file
- [ ] Internet connection stable
- [ ] Computer can run for hours/days
- [ ] Ready to monitor first trade

---

## 📊 RISK UNDERSTANDING

- [ ] I understand stop loss will automatically close losing trades
- [ ] I accept max loss per trade: ~18-90 pesos (1.5-1.8% of balance)
- [ ] I understand bot only trades 4-5 star setups (selective!)
- [ ] I know some weeks may have 0 trades (normal!)
- [ ] I accept trading carries risk of loss
- [ ] I'm starting with money I can afford to lose
- [ ] I will monitor the first few trades closely

---

## 🚨 EMERGENCY PROCEDURES

**If something goes wrong:**

### Stop the bot immediately:
```
Press Ctrl+C in the terminal
```

### Close any open positions manually:
1. Log in to Binance website/app
2. Go to Spot Trading
3. Find open BTC/USDT order
4. Click "Cancel" or "Close Position"

### Disable API keys (if compromised):
1. Binance > Profile > API Management
2. Click "Delete" next to your API key
3. Confirm deletion

---

## 📞 SUPPORT CONTACTS

**Binance Support:**
- Website: https://www.binance.com/en/support
- Live Chat: Available 24/7 in Binance app

**Bot Issues:**
- Check error message carefully
- Review PRODUCTION_DEPLOYMENT.md troubleshooting section
- Share error message with developer

---

## ✅ FINAL GO/NO-GO

**All items checked above?**

- [ ] YES - I'm ready to go live! → Run `python range_fvg_bot_micro.py`
- [ ] NO - Missing items: ___________________________

**Date:** ____/____/____
**Time:** ____:____
**Capital:** _____ pesos / _____ USDT
**Win rate goal:** 75-85%
**Expected profit/month:** _____ pesos

---

## 🎯 First Trade Monitoring

**When bot places first trade, check:**

- [ ] Order appeared on Binance (app/website)
- [ ] Direction correct (LONG or SHORT)
- [ ] Entry price looks reasonable
- [ ] Stop loss set automatically
- [ ] Take profit set automatically
- [ ] Position size matches expectations
- [ ] No errors in terminal

**After first trade closes:**

- [ ] Result: WIN ✅ / LOSS ❌
- [ ] P&L: _____ pesos
- [ ] Bot behavior as expected
- [ ] Balance updated correctly
- [ ] Ready for next trade

---

## 📈 Week 1 Review

**After first week, evaluate:**

- Total trades: _____
- Wins: _____
- Losses: _____
- Win rate: _____%
- Total P&L: _____ pesos
- Expected performance: 75-85% win rate

**Decision:**
- [ ] Continue trading (performance good)
- [ ] Adjust settings (needs tweaking)
- [ ] Add more capital (if profitable)
- [ ] Stop trading (if unprofitable/uncomfortable)

---

## 🛡️ Safety Reminders

### The bot will NOT:
- ❌ Trade more than once per day (default)
- ❌ Risk more than 1.5% per trade
- ❌ Trade without stop loss
- ❌ Exceed daily loss limit ($2 / ~125 pesos)
- ❌ Trade low-quality setups (only 4-5 stars)

### The bot WILL:
- ✅ Automatically set stop loss on every trade
- ✅ Automatically set take profit (2:1 ratio)
- ✅ Skip weak setups (quality filter)
- ✅ Stop trading if daily loss limit hit
- ✅ Show all actions in terminal

---

## 🎓 Remember

**"The best trade is the one you don't take"**

The bot is designed to be **ultra-selective**. Don't worry if you see:
- ⏭️ Skipped setups (good! avoiding losers)
- Days with no trades (good! waiting for quality)
- Fewer trades than expected (good! quality > quantity)

**Trust the process!**

---

**Ready?** → All boxes checked? → Go live! 🚀

**Not ready?** → Review PRODUCTION_DEPLOYMENT.md again

---

**Last updated:** 2025-11-17
**Bot version:** Micro Capital v1.0
