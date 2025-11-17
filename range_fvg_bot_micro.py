#!/usr/bin/env python3
"""
Range FVG Bot - Micro Capital Version
Optimized for small accounts ($18-100 USD / 1,000-5,000 pesos)

Key features:
- Uses v2.1 logic (ultra-selective, high win rate)
- Lower risk per trade (1% instead of 2%)
- Minimum 4-star setups only
- Max 1 trade per day (conservative)
- Fee-aware position sizing
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
import pytz
import json
import os
import sys

class MicroCapitalBot:
    def __init__(self, config_file='config_live.json'):
        """Initialize micro-capital bot"""

        # Load config
        self.config = self.load_config(config_file)

        exchange_config = self.config['exchange']
        bot_settings = self.config['bot_settings']
        self.strategy_params = self.config['strategy_parameters']
        self.risk_mgmt = self.config['risk_management']
        time_settings = self.config['time_settings']

        self.symbol = bot_settings['symbol']
        self.paper_trading = bot_settings['paper_trading']

        # Initialize exchange
        self.exchange = self.setup_exchange(exchange_config)

        # Timezone
        self.timezone = pytz.timezone(time_settings['timezone'])

        # Range tracking
        self.daily_range = {
            'high': None,
            'low': None,
            'date': None,
            'marked': False
        }

        # Position tracking
        self.position = None
        self.pending_order = None

        # Balance
        if self.paper_trading:
            self.balance = bot_settings['initial_balance']
            self.initial_balance = bot_settings['initial_balance']
        else:
            self.update_real_balance()

        self.trades_history = []
        self.daily_trades = 0
        self.daily_loss = 0

        # MICRO CAPITAL SETTINGS (Stricter than normal)
        self.volume_multiplier = 2.0  # High volume required
        self.ema_period = 50
        self.atr_period = 14
        self.min_atr_multiplier = 1.3
        self.min_quality_stars = 4  # Only 4-5 star setups!

        self.time_settings = time_settings

        print(f"\n{'='*60}")
        print(f"🤖 MICRO CAPITAL BOT - v2.1 Logic")
        print(f"{'='*60}")
        print(f"Capital: ${self.balance:.2f} USDT")
        print(f"Mode: {'PAPER TRADING' if self.paper_trading else 'LIVE TRADING'}")
        print(f"Risk/Trade: {self.strategy_params['risk_per_trade']*100}%")
        print(f"Min Quality: {self.min_quality_stars} stars")
        print(f"Max Daily Trades: {self.risk_mgmt['max_daily_trades']}")
        print(f"Timezone: {time_settings['timezone']}")
        print(f"{'='*60}\n")

        if self.balance < 15:
            print(f"⚠️ WARNING: Balance ${self.balance:.2f} is very small!")
            print(f"Expected profit per trade: $0.30-0.50")
            print(f"Fees will take ~20% of profits")
            print(f"Recommend minimum $50 for better results\n")

    def load_config(self, config_file):
        """Load config file"""
        if not os.path.exists(config_file):
            print(f"❌ Config not found: {config_file}")
            sys.exit(1)

        with open(config_file, 'r') as f:
            return json.load(f)

    def setup_exchange(self, exchange_config):
        """Setup exchange with API keys"""
        exchange_params = {'enableRateLimit': True}

        if not self.paper_trading:
            api_key = exchange_config.get('api_key', '')
            api_secret = exchange_config.get('api_secret', '')

            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                print("❌ No API key! Add to config_live.json")
                sys.exit(1)

            exchange_params['apiKey'] = api_key
            exchange_params['secret'] = api_secret

        return ccxt.binance(exchange_params)

    def update_real_balance(self):
        """Get real USDT balance"""
        try:
            balance = self.exchange.fetch_balance()
            self.balance = balance['USDT']['free']
            self.initial_balance = self.balance
            print(f"✅ Real balance: ${self.balance:.2f} USDT")
        except Exception as e:
            print(f"❌ Error fetching balance: {e}")
            sys.exit(1)

    def get_current_time(self):
        """Get current time in configured timezone"""
        return datetime.now(self.timezone)

    def is_market_open_time(self):
        """Check if during market hours"""
        current_time = self.get_current_time()

        market_open_str = self.time_settings['market_open']
        market_close_str = self.time_settings['market_close']

        market_open = current_time.replace(
            hour=int(market_open_str.split(':')[0]),
            minute=int(market_open_str.split(':')[1]),
            second=0, microsecond=0
        )
        market_close = current_time.replace(
            hour=int(market_close_str.split(':')[0]),
            minute=int(market_close_str.split(':')[1]),
            second=0, microsecond=0
        )

        return market_open <= current_time <= market_close

    def should_mark_range(self):
        """Check if should mark range"""
        current_time = self.get_current_time()

        range_end_str = self.time_settings['range_end_time']
        range_mark_time = current_time.replace(
            hour=int(range_end_str.split(':')[0]),
            minute=int(range_end_str.split(':')[1]),
            second=0, microsecond=0
        )

        current_date = current_time.date()

        if self.daily_range['date'] != current_date:
            self.daily_range['marked'] = False
            self.daily_range['date'] = current_date
            self.daily_trades = 0
            self.daily_loss = 0

        return current_time >= range_mark_time and not self.daily_range['marked']

    def can_enter_trade(self):
        """Check if can enter trades"""
        current_time = self.get_current_time()

        entry_cutoff_str = self.time_settings['entry_cutoff_time']
        entry_cutoff = current_time.replace(
            hour=int(entry_cutoff_str.split(':')[0]),
            minute=int(entry_cutoff_str.split(':')[1]),
            second=0, microsecond=0
        )

        time_ok = current_time < entry_cutoff
        trades_ok = self.daily_trades < self.risk_mgmt['max_daily_trades']
        loss_ok = abs(self.daily_loss) < self.risk_mgmt['max_daily_loss_usd']

        return time_ok and trades_ok and loss_ok

    def get_candles(self, timeframe='5m', limit=100):
        """Fetch candles"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(self.timezone)
            return df
        except Exception as e:
            print(f"❌ Error fetching candles: {e}")
            return None

    def calculate_ema(self, df, period=50):
        """Calculate EMA"""
        return df['close'].ewm(span=period, adjust=False).mean()

    def calculate_atr(self, df, period=14):
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        return true_range.rolling(period).mean()

    def get_trend_direction(self, df):
        """Get trend direction"""
        if len(df) < self.ema_period:
            return 'NEUTRAL'

        ema = self.calculate_ema(df, self.ema_period)
        current_price = df.iloc[-1]['close']
        current_ema = ema.iloc[-1]

        if current_price > current_ema * 1.01:
            return 'BULLISH'
        elif current_price < current_ema * 0.99:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def check_volatility(self, df):
        """Check volatility"""
        if len(df) < self.atr_period * 2:
            return False

        atr = self.calculate_atr(df, self.atr_period)
        current_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-50:].mean()

        return current_atr > (avg_atr * self.min_atr_multiplier)

    def check_volume(self, candle, df):
        """Check volume"""
        if len(df) < 20:
            return False

        avg_volume = df['volume'].iloc[-20:].mean()
        return candle['volume'] > (avg_volume * self.volume_multiplier)

    def mark_daily_range(self):
        """Mark daily range"""
        try:
            df = self.get_candles(timeframe='15m', limit=10)
            if df is None or len(df) == 0:
                return False

            current_time = self.get_current_time()
            current_date = current_time.date()

            range_start_str = self.time_settings['range_start_time']
            range_hour = int(range_start_str.split(':')[0])
            range_minute = int(range_start_str.split(':')[1])

            for idx, row in df.iterrows():
                candle_time = row['timestamp']
                if (candle_time.date() == current_date and
                    candle_time.hour == range_hour and
                    candle_time.minute == range_minute):

                    self.daily_range['high'] = row['high']
                    self.daily_range['low'] = row['low']
                    self.daily_range['marked'] = True
                    self.daily_range['date'] = current_date

                    print(f"\n{'='*60}")
                    print(f"📊 RANGE MARKED")
                    print(f"High: ${self.daily_range['high']:,.2f}")
                    print(f"Low: ${self.daily_range['low']:,.2f}")
                    print(f"{'='*60}\n")

                    return True

            print(f"⏳ Waiting for range candle...")
            return False

        except Exception as e:
            print(f"❌ Error marking range: {e}")
            return False

    def detect_fair_value_gap(self, df):
        """Detect FVG (same as v2.1)"""
        if not self.daily_range['marked'] or len(df) < 3:
            return None

        candle1 = df.iloc[-3]
        candle2 = df.iloc[-2]
        candle3 = df.iloc[-1]

        range_high = self.daily_range['high']
        range_low = self.daily_range['low']

        # Bullish FVG
        bullish_gap_bottom = candle1['high']
        bullish_gap_top = candle3['low']

        if bullish_gap_top > bullish_gap_bottom:
            candles_close_above = sum([
                candle1['close'] > range_high,
                candle2['close'] > range_high,
                candle3['close'] > range_high
            ])

            candles_touch_range = sum([
                candle1['low'] <= range_high,
                candle2['low'] <= range_high,
                candle3['low'] <= range_high
            ])

            if candles_close_above >= 1 and candles_touch_range >= 1:
                fvg_price = (bullish_gap_bottom + bullish_gap_top) / 2

                return {
                    'type': 'BULLISH',
                    'direction': 'LONG',
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['low'] * 0.999,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        # Bearish FVG
        bearish_gap_top = candle1['low']
        bearish_gap_bottom = candle3['high']

        if bearish_gap_top > bearish_gap_bottom:
            candles_close_below = sum([
                candle1['close'] < range_low,
                candle2['close'] < range_low,
                candle3['close'] < range_low
            ])

            candles_touch_range = sum([
                candle1['high'] >= range_low,
                candle2['high'] >= range_low,
                candle3['high'] >= range_low
            ])

            if candles_close_below >= 1 and candles_touch_range >= 1:
                fvg_price = (bearish_gap_top + bearish_gap_bottom) / 2

                return {
                    'type': 'BEARISH',
                    'direction': 'SHORT',
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['high'] * 1.001,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3,
                    'timestamp': candle3['timestamp']
                }

        return None

    def score_setup_quality(self, fvg, df_5m, df_1h, volume_ok, volatility_ok, trend):
        """Score setup (v2.1 logic)"""
        score = 1

        if volume_ok:
            score += 1

        if volatility_ok:
            score += 1

        if trend == fvg['type']:
            score += 1

        if df_1h is not None and len(df_1h) > 0:
            trend_1h = self.get_trend_direction(df_1h)
            if trend_1h == fvg['type']:
                score += 1

        return score

    def calculate_position_size(self, entry_price, stop_loss):
        """Calculate position size for micro capital"""
        # Lower risk for micro capital
        risk_amount = self.balance * self.strategy_params['risk_per_trade']
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit

        # Round to exchange precision (usually 0.00001 for BTC)
        position_size = round(position_size, 5)

        # Check minimum order size (~$10)
        min_order_value = 10
        order_value = position_size * entry_price

        if order_value < min_order_value:
            print(f"⚠️ Order value ${order_value:.2f} below minimum ${min_order_value}")
            return 0

        return position_size

    def create_limit_order(self, fvg, setup_quality):
        """Create limit order"""
        if not self.can_enter_trade():
            return

        if self.pending_order or self.position:
            return

        entry_price = fvg['fvg_price']
        stop_loss = fvg['stop_loss']

        risk = abs(entry_price - stop_loss)

        if fvg['direction'] == 'LONG':
            take_profit = entry_price + (risk * self.strategy_params['reward_ratio'])
        else:
            take_profit = entry_price - (risk * self.strategy_params['reward_ratio'])

        position_size = self.calculate_position_size(entry_price, stop_loss)

        if position_size == 0:
            print(f"❌ Position size too small to trade")
            return

        self.pending_order = {
            'direction': fvg['direction'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'created_at': fvg['timestamp'],
            'setup_quality': setup_quality
        }

        stars = "⭐" * setup_quality
        print(f"\n{'='*60}")
        print(f"🎯 LIMIT ORDER CREATED {stars}")
        print(f"Direction: {fvg['direction']}")
        print(f"Entry: ${entry_price:,.2f}")
        print(f"Stop: ${stop_loss:,.2f}")
        print(f"Target: ${take_profit:,.2f}")
        print(f"Size: {position_size:.5f} BTC")
        print(f"Risk: ${risk * position_size:.2f}")
        print(f"Reward: ${risk * position_size * self.strategy_params['reward_ratio']:.2f}")
        print(f"{'='*60}\n")

    def check_limit_order_fill(self, current_price):
        """Check if limit order filled"""
        if not self.pending_order:
            return

        order = self.pending_order
        filled = False

        if order['direction'] == 'LONG':
            if current_price <= order['entry_price']:
                filled = True
        else:
            if current_price >= order['entry_price']:
                filled = True

        if filled:
            self.position = {
                'direction': order['direction'],
                'entry_price': order['entry_price'],
                'stop_loss': order['stop_loss'],
                'take_profit': order['take_profit'],
                'position_size': order['position_size'],
                'entry_time': datetime.now(self.timezone),
                'setup_quality': order['setup_quality']
            }

            self.daily_trades += 1

            print(f"\n✅ ORDER FILLED @ ${order['entry_price']:,.2f}")
            self.pending_order = None

    def check_exit_conditions(self, current_high, current_low):
        """Check exit conditions"""
        if not self.position:
            return

        pos = self.position
        exit_price = None
        exit_reason = None

        if pos['direction'] == 'LONG':
            if current_low <= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
            elif current_high >= pos['take_profit']:
                exit_price = pos['take_profit']
                exit_reason = 'Take Profit'
        else:
            if current_high >= pos['stop_loss']:
                exit_price = pos['stop_loss']
                exit_reason = 'Stop Loss'
            elif current_low <= pos['take_profit']:
                exit_price = pos['take_profit']
                exit_reason = 'Take Profit'

        if exit_price:
            self.close_position(exit_price, exit_reason)

    def close_position(self, exit_price, reason):
        """Close position"""
        if not self.position:
            return

        pos = self.position

        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        # Account for fees (0.1% × 2 = 0.2% total)
        order_value = pos['position_size'] * pos['entry_price']
        fees = order_value * 0.002  # 0.2%
        pnl_after_fees = pnl - fees

        self.balance += pnl_after_fees
        self.daily_loss += pnl_after_fees if pnl_after_fees < 0 else 0

        trade = {
            'entry_time': str(pos['entry_time']),
            'exit_time': str(datetime.now(self.timezone)),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'position_size': pos['position_size'],
            'setup_quality': pos['setup_quality'],
            'pnl_gross': pnl,
            'fees': fees,
            'pnl_net': pnl_after_fees,
            'reason': reason,
            'balance': self.balance
        }

        self.trades_history.append(trade)

        pnl_emoji = "💚" if pnl_after_fees > 0 else "❤️"
        print(f"\n{'='*60}")
        print(f"{pnl_emoji} POSITION CLOSED - {reason}")
        print(f"P&L Gross: ${pnl:.2f}")
        print(f"Fees: ${fees:.2f}")
        print(f"P&L Net: ${pnl_after_fees:.2f}")
        print(f"Balance: ${self.balance:.2f}")
        print(f"ROI: {((self.balance - self.initial_balance) / self.initial_balance) * 100:.2f}%")
        print(f"{'='*60}\n")

        self.position = None
        self.save_log()

    def save_log(self):
        """Save log"""
        try:
            os.makedirs(os.path.dirname(self.config['logging']['log_file']), exist_ok=True)

            log_data = {
                'initial_balance': self.initial_balance,
                'current_balance': self.balance,
                'total_pnl': self.balance - self.initial_balance,
                'roi': ((self.balance - self.initial_balance) / self.initial_balance) * 100,
                'total_trades': len(self.trades_history),
                'trades': self.trades_history
            }

            with open(self.config['logging']['log_file'], 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            print(f"❌ Error saving log: {e}")

    def run(self):
        """Main loop"""
        print(f"✅ Bot started\n")

        try:
            while True:
                current_time = self.get_current_time()

                if self.should_mark_range():
                    self.mark_daily_range()

                if not self.is_market_open_time():
                    print(f"[{current_time.strftime('%H:%M')}] Market closed. Waiting...")
                    time.sleep(300)
                    continue

                df_5m = self.get_candles(timeframe='5m', limit=100)

                if df_5m is None or len(df_5m) < 3:
                    time.sleep(60)
                    continue

                current_candle = df_5m.iloc[-1]
                current_price = current_candle['close']

                status = f"[{current_time.strftime('%H:%M')}] ${current_price:,.2f} | ${self.balance:.2f}"

                if self.position:
                    status += f" | Position: {self.position['direction']}"
                elif self.pending_order:
                    status += f" | Pending: {self.pending_order['direction']}"
                else:
                    status += " | Watching"

                print(status)

                if self.pending_order:
                    self.check_limit_order_fill(current_price)

                if self.position:
                    self.check_exit_conditions(current_candle['high'], current_candle['low'])

                if not self.position and not self.pending_order and self.daily_range['marked']:
                    fvg = self.detect_fair_value_gap(df_5m)

                    if fvg:
                        df_1h = self.get_candles(timeframe='1h', limit=100)

                        trend_5m = self.get_trend_direction(df_5m)
                        volatility_ok = self.check_volatility(df_5m)
                        volume_ok = self.check_volume(fvg['candle2'], df_5m)

                        setup_quality = self.score_setup_quality(
                            fvg, df_5m, df_1h, volume_ok, volatility_ok, trend_5m
                        )

                        stars = "⭐" * setup_quality

                        if setup_quality >= self.min_quality_stars:
                            if trend_5m == fvg['type']:
                                print(f"\n🔍 {fvg['type']} FVG {stars}")
                                self.create_limit_order(fvg, setup_quality)
                            else:
                                print(f"⏭️  Skipped: Trend mismatch {stars}")
                        else:
                            print(f"⏭️  Skipped: Need {self.min_quality_stars}+ stars {stars}")

                time.sleep(60)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Bot stopped")
            self.save_log()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.save_log()


if __name__ == "__main__":
    bot = MicroCapitalBot(config_file='config_live.json')
    bot.run()
