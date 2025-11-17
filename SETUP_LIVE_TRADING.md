# 🚀 Live Trading Setup Guide

Complete guide to set up the Range FVG Bot for live trading on Binance.

---

## ⚠️ IMPORTANT: Capital Requirements

**Your mentioned budget: 500 pesos (~$8-9 USD)**

### ❌ This is TOO SMALL for this strategy

**Why:**
- Binance minimum order: **$10 USD**
- Recommended minimum: **$100-500 USD** (5,000-25,000 pesos)
- Ideal starting capital: **$1,000+ USD** (50,000+ pesos)

**With 500 pesos ($8-9):**
- Cannot meet minimum order sizes
- Fees will eat all profits (0.1% = $0.009 per trade)
- Cannot manage risk (2% of $9 = $0.18)

### ✅ Recommendations:

**Option 1: Save More Capital**
- Save up to **5,000-10,000 pesos** ($100-200 USD)
- This allows proper risk management
- Start small but viable

**Option 2: Paper Trade While Saving**
- Use `python range_fvg_bot.py` (paper trading)
- Practice with fake money
- Build experience while saving capital

**Option 3: Try Grid Trading** (if you want to start with 500 pesos)
- Grid trading can work with smaller capital
- Different strategy than this bot
- Let me know if you want a grid bot instead

---

## 📋 Prerequisites

Before you start, make sure you have:

- [ ] **Minimum $100 USD** (5,000+ pesos) to trade
- [ ] Valid ID for KYC verification
- [ ] Smartphone with Google Authenticator
- [ ] Basic understanding of trading risks

---

## 🏦 Step 1: Create Binance Account

### 1.1 Sign Up

1. Go to [binance.com](https://www.binance.com)
2. Click **Register**
3. Enter email and create strong password
4. Verify email

### 1.2 Complete KYC Verification

**Required for trading:**
1. Go to **Profile** → **Identification**
2. Select **Verify Now**
3. Choose **ID Card** or **Passport**
4. Upload clear photo of ID
5. Take selfie for verification
6. Wait 10-30 minutes for approval

### 1.3 Enable 2FA (Security)

**CRITICAL for account security:**
1. Download **Google Authenticator** app
2. Go to **Security** → **2FA**
3. Scan QR code with app
4. Save backup codes somewhere safe
5. Enable 2FA for withdrawals

---

## 💰 Step 2: Deposit Funds

### Option A: P2P Trading (Recommended - Best Rates)

1. Click **Buy Crypto** → **P2P Trading**
2. Select **USDT** (Tether stablecoin)
3. Choose **PHP** as currency
4. Select amount (minimum 500-1000 pesos for testing)
5. Choose payment method:
   - **GCash** (instant)
   - **PayMaya** (instant)
   - **Bank Transfer** (1-2 hours)
6. Find seller with:
   - ✅ High completion rate (>95%)
   - ✅ Many trades (500+)
   - ✅ Good price
7. Click **Buy USDT**
8. Follow payment instructions
9. Confirm payment in Binance
10. Wait for seller to release USDT (usually 5-15 min)

### Option B: Direct Bank Deposit

1. Click **Buy Crypto** → **Bank Deposit**
2. Select **PHP**
3. Choose bank (UnionBank, BDO, BPI, etc.)
4. Enter amount
5. Get bank details from Binance
6. Transfer from your bank
7. Upload proof of payment
8. Wait 1-2 hours for confirmation

**After deposit, you'll have USDT in your Spot Wallet**

---

## 🔑 Step 3: Create API Keys

### 3.1 Generate API Key

1. Log into Binance
2. Hover over **Profile Icon** → **API Management**
3. Click **Create API**
4. Choose **System Generated**
5. Label: `Range Scalping Bot`
6. Click **Next**
7. Complete 2FA verification

### 3.2 Configure API Permissions

**IMPORTANT: Set correct permissions**

✅ **Enable:**
- **Enable Reading** (to check balance and positions)
- **Enable Spot & Margin Trading** (to place trades)

❌ **DISABLE (for safety):**
- **Enable Withdrawals** ← Keep this OFF!
- **Enable Futures** ← Keep this OFF!
- **Enable Vanilla Options** ← Keep this OFF!

### 3.3 Copy Your Keys

You'll see:
- **API Key**: `xxxxxxxxxxx` (copy this)
- **Secret Key**: `xxxxxxxxxxx` (copy this - shown once!)

**⚠️ IMPORTANT:**
- Save these keys somewhere safe
- **NEVER share them** with anyone
- Secret key is shown **only once**
- If lost, delete and create new keys

### 3.4 IP Whitelist (Optional but Recommended)

1. Click **Edit restrictions**
2. Select **Restrict access to trusted IPs only**
3. Add your IP address
4. Confirm changes

**To find your IP:**
- Google "what is my ip"
- Copy the IP address shown
- Add it to Binance

---

## ⚙️ Step 4: Configure the Bot

### 4.1 Edit Configuration File

Open `config_live.json` and add your API keys:

```json
{
  "exchange": {
    "name": "binance",
    "api_key": "PASTE_YOUR_API_KEY_HERE",
    "api_secret": "PASTE_YOUR_SECRET_KEY_HERE",
    "testnet": false
  },
  "bot_settings": {
    "symbol": "BTC/USDT",
    "paper_trading": true,  ← START with true!
    "initial_balance": 10000
  },
  "risk_management": {
    "max_position_size_usd": 50,  ← Adjust based on capital
    "max_daily_loss_usd": 10,     ← Max $10 loss per day
    "max_daily_trades": 3
  }
}
```

### 4.2 Adjust Risk Settings

**For $100 capital (5,000 pesos):**
```json
"risk_management": {
  "max_position_size_usd": 30,
  "max_daily_loss_usd": 10,
  "max_daily_trades": 2
}
```

**For $500 capital (25,000 pesos):**
```json
"risk_management": {
  "max_position_size_usd": 100,
  "max_daily_loss_usd": 25,
  "max_daily_trades": 3
}
```

**For $1000 capital (50,000 pesos):**
```json
"risk_management": {
  "max_position_size_usd": 200,
  "max_daily_loss_usd": 50,
  "max_daily_trades": 3
}
```

---

## 🧪 Step 5: Test with Paper Trading FIRST

### 5.1 Run Paper Trading Mode

**ALWAYS test first with paper trading:**

```powershell
python range_fvg_bot_live.py
```

Make sure in `config_live.json`:
```json
"paper_trading": true  ← Must be true!
```

### 5.2 Monitor for 1-2 Weeks

**What to watch:**
- Win rate (should be 65-85%)
- Average profit per trade
- Max drawdown
- Bot stability (no crashes)

### 5.3 Verify Everything Works

- [ ] Bot connects to Binance successfully
- [ ] Daily range is marked correctly
- [ ] Fair Value Gaps are detected
- [ ] Orders are simulated properly
- [ ] Stop loss and take profit work
- [ ] No errors or crashes

---

## 🔴 Step 6: Go Live (Only After Testing!)

### 6.1 Enable Live Trading

**⚠️ ONLY after 1-2 weeks of successful paper trading:**

Edit `config_live.json`:
```json
{
  "bot_settings": {
    "paper_trading": false  ← Change to false
  }
}
```

### 6.2 Start the Bot

```powershell
python range_fvg_bot_live.py
```

**You'll see a warning:**
```
⚠️  WARNING: LIVE TRADING MODE ENABLED ⚠️
Real money will be used for trading!
Type 'YES' to confirm and continue:
```

Type `YES` to confirm.

### 6.3 Monitor Closely

**First week of live trading:**
- Check the bot multiple times per day
- Verify trades are executed correctly
- Watch for any errors
- Keep logs of all trades

---

## 📊 Understanding Fees

### Binance Fee Structure

**Spot Trading Fees:**
- **Maker fee:** 0.1% (when limit order is placed)
- **Taker fee:** 0.1% (when market order is filled)

**With BNB discount:**
- **Fee:** 0.075% (save 25%)

**How to get BNB discount:**
1. Buy some BNB (Binance Coin)
2. Enable **Use BNB to pay fees** in settings
3. Fees automatically reduced by 25%

### Fee Examples

**$100 trade:**
- Fee without BNB: $0.10 (0.1%)
- Fee with BNB: $0.075 (0.075%)
- **Savings: $0.025**

**$1000 trade:**
- Fee without BNB: $1.00
- Fee with BNB: $0.75
- **Savings: $0.25**

**For 30 trades/month at $100 each:**
- Total fees without BNB: $6
- Total fees with BNB: $4.50
- **Monthly savings: $1.50**

---

## 🛡️ Risk Management Rules

### Golden Rules:

1. **Never risk more than 2% per trade**
2. **Max 3 trades per day**
3. **Stop if daily loss hits limit**
4. **Never remove stop loss**
5. **Don't override the bot manually**
6. **Start with minimum capital**
7. **Withdraw profits regularly**

### Position Sizing

The bot calculates this automatically, but here's how:

**Example with $500 capital:**
- Risk per trade: 2% = $10
- Entry: $95,000
- Stop loss: $94,500
- Risk per BTC: $500
- Position size: $10 / $500 = 0.02 BTC
- Total position value: 0.02 × $95,000 = $1,900

**If stop loss hits:** Lose $10 (2% of capital)
**If take profit hits:** Gain $20 (4% of capital) ← 2:1 ratio

---

## 📱 Monitoring Your Bot

### Daily Checklist:

- [ ] Check bot is running (no crashes)
- [ ] Verify daily range was marked
- [ ] Review any trades taken
- [ ] Check profit/loss
- [ ] Verify no errors in logs

### Weekly Review:

- [ ] Calculate win rate
- [ ] Review total P&L
- [ ] Check if performance matches backtest
- [ ] Adjust parameters if needed

---

## 🚨 Troubleshooting

### Bot won't start:
```
❌ ERROR: No API key configured!
```
**Fix:** Edit `config_live.json` and add your API keys

### Authentication error:
```
❌ Error fetching balance: Authentication failed
```
**Fix:**
- Verify API keys are correct
- Check API permissions are enabled
- Regenerate keys if needed

### Minimum order size error:
```
❌ Order value too small
```
**Fix:** Increase capital or max_position_size_usd

### IP restriction error:
```
❌ IP address not whitelisted
```
**Fix:** Add your IP to Binance API whitelist

---

## 💡 Best Practices

### Do's:
✅ Start with paper trading
✅ Test for 1-2 weeks minimum
✅ Keep API secret key safe
✅ Monitor the bot daily
✅ Withdraw profits weekly
✅ Keep logs of all trades
✅ Start with minimum capital

### Don'ts:
❌ Don't share API keys
❌ Don't enable withdrawal permissions
❌ Don't skip paper trading
❌ Don't use money you can't afford to lose
❌ Don't manually interfere with trades
❌ Don't increase risk after losses
❌ Don't trade with 500 pesos ($9)

---

## 📞 Support

**If you have issues:**

1. Check the error message
2. Review this guide again
3. Check Binance API status
4. Verify your internet connection
5. Check bot logs in `logs/trading_bot.log`

**Common issues are usually:**
- Incorrect API keys
- Wrong permissions
- Insufficient capital
- Network problems

---

## ⚖️ Final Warning

**IMPORTANT DISCLAIMERS:**

- Trading involves substantial risk of loss
- Past performance doesn't guarantee future results
- Only trade with money you can afford to lose
- This bot is provided as-is, no guarantees
- The creator is not responsible for any losses
- **Start small and test thoroughly**
- **500 pesos ($9) is NOT enough for this strategy**

---

## 🎯 Recommended Path

**For someone with 500 pesos:**

1. **Save more capital** (target: 5,000-10,000 pesos)
2. **Paper trade while saving** (gain experience)
3. **Study the strategy** (understand how it works)
4. **Run backtests** (verify it works)
5. **Start with 5,000+ pesos** (when ready)
6. **Go live with caution** (small positions first)

**Timeline:**
- Week 1-2: Paper trading + save money
- Week 3-4: More paper trading + backtesting
- Week 5+: Live trading (when capital ready)

---

## 📚 Next Steps

Once your capital is ready:

1. ✅ Complete Binance account setup
2. ✅ Get API keys
3. ✅ Edit `config_live.json`
4. ✅ Run paper trading for 1-2 weeks
5. ✅ Verify win rate and profitability
6. ✅ Go live with caution

Good luck and trade safely! 🚀
