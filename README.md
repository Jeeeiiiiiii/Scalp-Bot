# BTC Scalping Bot - Paper Trading

A Bitcoin scalping bot based on supply/demand zone strategy with full-bodied candle confirmation.

## Strategy Overview

This bot implements the exact strategy from your trading images:

### Entry Rules
1. **Timeframe**: 5-minute candles
2. **Setup Identification**: 
   - For SELL: Look for price approaching supply zones (previous lows)
   - For BUY: Look for price approaching demand zones (previous highs)
3. **Entry Trigger**: 
   - SELL: Full-bodied bearish candle closes BELOW previous low
   - BUY: Full-bodied bullish candle closes ABOVE previous high
4. **Confirmation**: Always wait for candle to fully close before entry

### Position Management
- **Stop Loss**: 
  - SELL: Above the supply zone/candle high
  - BUY: Below the demand zone/candle low
- **Take Profit**: 1:1 risk-reward ratio
- **Position Size**: 10% of account balance per trade

### Exit Rules
1. Stop loss is hit
2. Take profit is reached
3. **Immediate exit** if price returns to entry level (key rule from your strategy!)

### Full-Bodied Candle Definition
- Candle body must be at least 60% of total candle range
- Shows strong directional conviction
- Reduces false signals

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt --break-system-packages
```

2. Run the bot:
```bash
python3 btc_scalping_bot.py
```

## Features

✅ **Paper Trading Mode** - Practice without risking real money
✅ **Full-bodied candle detection** - Only trades high-conviction setups
✅ **1:1 Risk-Reward** - Conservative scalping approach
✅ **Auto Stop Loss & Take Profit** - Automated risk management
✅ **Exit on entry return** - Protects capital when momentum fades
✅ **Detailed logging** - All trades saved to JSON file
✅ **Real-time monitoring** - Live price and position updates

## Configuration

Edit these parameters in `btc_scalping_bot.py`:

```python
# Trading parameters
symbol = 'BTC/USDT'          # Trading pair
timeframe = '5m'             # 5-minute candles
paper_balance = 10000        # Starting balance
min_body_ratio = 0.6         # Minimum body ratio for "full-bodied" candle
lookback_candles = 20        # Candles to analyze for zones
```

## Output

The bot creates a log file at: `/mnt/user-data/outputs/scalping_bot_log.json`

This includes:
- All trade entries and exits
- P&L for each trade
- Current balance
- Position details

## Strategy Validation

Before going live, run the bot in paper trading mode for at least 1-2 weeks to validate:
- Win rate percentage
- Average profit per trade
- Maximum drawdown
- Risk-reward consistency

**Only move to live trading after proving profitability in paper trading!**

## Safety Features

1. **Paper trading by default** - Must explicitly enable live trading
2. **Position size limits** - Max 10% per trade
3. **Automatic stop losses** - Every position protected
4. **Exit on reversal** - Closes if price returns to entry

## Next Steps

1. ✅ Run bot in paper trading mode
2. ✅ Monitor performance for 1-2 weeks
3. ✅ Analyze win rate and profitability
4. ✅ Adjust parameters if needed
5. ⚠️ Only then consider live trading with small amounts

## Warning

⚠️ **This bot is for educational purposes. Trading cryptocurrencies involves substantial risk. Never trade with money you can't afford to lose. Past performance doesn't guarantee future results.**

## Disclaimer

This trading bot is provided as-is. The creator is not responsible for any financial losses incurred through its use. Always do your own research and trade responsibly.
