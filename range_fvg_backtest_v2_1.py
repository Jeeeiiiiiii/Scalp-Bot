#!/usr/bin/env python3
"""
Ultra-Selective Range FVG Strategy v2.1 - BACKTEST
Based on v2.0 analysis: 3-star setups had 33% win rate (too low!)

v2.1 Improvements:
1. Minimum 4-star quality required (up from 3)
2. Stronger volume requirement (2.0x instead of 1.5x)
3. Stricter trend alignment
4. Will trade 0 times if no quality setups (that's GOOD!)
5. Only trades PERFECT or NEAR-PERFECT setups

Philosophy: "It's better to make $0 than lose money on bad setups"
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import pytz
import json
import os

class RangeFVGBacktestV2_1:
    def __init__(self, initial_balance=10000, risk_per_trade=0.02, reward_ratio=2):
        """Initialize ultra-selective backtest"""
        self.exchange = ccxt.binance({'enableRateLimit': True})
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.reward_ratio = reward_ratio

        self.est = pytz.timezone('America/New_York')

        self.trades = []
        self.position = None
        self.pending_order = None
        self.daily_range = None

        # STRICTER parameters for v2.1
        self.volume_multiplier = 2.0  # Increased from 1.5x to 2.0x
        self.ema_period = 50
        self.atr_period = 14
        self.min_atr_multiplier = 1.3  # Increased from 1.2x to 1.3x
        self.min_quality_stars = 4  # Increased from 3 to 4 stars

    def fetch_historical_data(self, symbol='BTC/USDT', timeframe='5m', days=7):
        """Fetch historical OHLCV data"""
        print(f"Fetching {days} days of {timeframe} data for {symbol}...")

        since = self.exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
        all_candles = []

        while True:
            try:
                candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                if not candles:
                    break
                all_candles.extend(candles)
                since = candles[-1][0] + 1

                if candles[-1][0] >= self.exchange.milliseconds() - (60 * 1000):
                    break

                import time
                time.sleep(0.5)

            except Exception as e:
                print(f"Error fetching data: {e}")
                break

        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(self.est)

        print(f"Fetched {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df

    def calculate_ema(self, df, period=50):
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        return true_range.rolling(period).mean()

    def get_trend_direction(self, df):
        """Determine trend direction using EMA"""
        if len(df) < self.ema_period:
            return 'NEUTRAL'

        ema = self.calculate_ema(df, self.ema_period)
        current_price = df.iloc[-1]['close']
        current_ema = ema.iloc[-1]

        # STRICTER trend requirement (1% instead of 0.5%)
        if current_price > current_ema * 1.01:  # 1% above EMA
            return 'BULLISH'
        elif current_price < current_ema * 0.99:  # 1% below EMA
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def check_volatility(self, df):
        """Check if current volatility is high enough"""
        if len(df) < self.atr_period * 2:
            return False

        atr = self.calculate_atr(df, self.atr_period)
        current_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-50:].mean()

        return current_atr > (avg_atr * self.min_atr_multiplier)

    def check_volume(self, candle, df):
        """Check if volume is high enough - STRICTER (2.0x)"""
        if len(df) < 20:
            return False

        avg_volume = df['volume'].iloc[-20:].mean()
        return candle['volume'] > (avg_volume * self.volume_multiplier)

    def mark_daily_range_from_15m(self, df_15m, current_date):
        """Mark the daily range from 15-minute data"""
        candle_930 = df_15m[
            (df_15m['timestamp'].dt.date == current_date) &
            (df_15m['timestamp'].dt.hour == 9) &
            (df_15m['timestamp'].dt.minute == 30)
        ]

        if len(candle_930) > 0:
            candle = candle_930.iloc[0]
            return {
                'high': candle['high'],
                'low': candle['low'],
                'date': current_date
            }

        return None

    def detect_fair_value_gap(self, candle1, candle2, candle3, range_high, range_low):
        """Detect Fair Value Gap pattern"""

        # BULLISH FVG
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
                    'gap_top': bullish_gap_top,
                    'gap_bottom': bullish_gap_bottom,
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['low'] * 0.999,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3
                }

        # BEARISH FVG
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
                    'gap_top': bearish_gap_top,
                    'gap_bottom': bearish_gap_bottom,
                    'fvg_price': fvg_price,
                    'stop_loss': candle1['high'] * 1.001,
                    'candle1': candle1,
                    'candle2': candle2,
                    'candle3': candle3
                }

        return None

    def score_setup_quality(self, fvg, df_5m, df_1h, volume_ok, volatility_ok, trend):
        """Score setup quality from 1-5 stars"""
        score = 1  # Baseline

        if volume_ok:
            score += 1

        if volatility_ok:
            score += 1

        # STRICTER: Trend must match (no NEUTRAL accepted)
        if trend == fvg['type']:
            score += 1

        # 1h confirmation
        if df_1h is not None and len(df_1h) > 0:
            trend_1h = self.get_trend_direction(df_1h)
            if trend_1h == fvg['type']:
                score += 1

        return score

    def calculate_position_size(self, entry_price, stop_loss, setup_quality):
        """Calculate position size - only 4-5 star setups"""
        if setup_quality < 4:  # Changed from 2 to 4
            return 0  # Skip anything below 4 stars

        # Adjust risk based on quality
        risk_multipliers = {
            5: 1.0,   # Full 2% risk
            4: 0.75,  # 1.5% risk
        }

        risk_multiplier = risk_multipliers.get(setup_quality, 0)
        adjusted_risk = self.risk_per_trade * risk_multiplier

        risk_amount = self.balance * adjusted_risk
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        return risk_amount / risk_per_unit

    def create_order(self, fvg, current_time, setup_quality):
        """Create order only for 4-5 star setups"""
        entry_price = fvg['fvg_price']
        stop_loss = fvg['stop_loss']

        risk = abs(entry_price - stop_loss)

        if fvg['direction'] == 'LONG':
            take_profit = entry_price + (risk * self.reward_ratio)
        else:
            take_profit = entry_price - (risk * self.reward_ratio)

        position_size = self.calculate_position_size(entry_price, stop_loss, setup_quality)

        if position_size == 0:
            return

        self.pending_order = {
            'direction': fvg['direction'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'created_at': current_time,
            'setup_quality': setup_quality
        }

    def check_order_fill(self, candle):
        """Check if order is filled"""
        if not self.pending_order:
            return False

        order = self.pending_order
        filled = False

        if order['direction'] == 'LONG':
            if candle['low'] <= order['entry_price']:
                filled = True
        else:
            if candle['high'] >= order['entry_price']:
                filled = True

        if filled:
            self.position = {
                'direction': order['direction'],
                'entry_price': order['entry_price'],
                'stop_loss': order['stop_loss'],
                'take_profit': order['take_profit'],
                'position_size': order['position_size'],
                'entry_time': candle['timestamp'],
                'setup_quality': order['setup_quality']
            }
            self.pending_order = None
            return True

        return False

    def check_exit(self, candle):
        """Check exit conditions"""
        if not self.position:
            return False, None, None

        pos = self.position

        if pos['direction'] == 'LONG':
            if candle['low'] <= pos['stop_loss']:
                return True, pos['stop_loss'], 'Stop Loss'
            if candle['high'] >= pos['take_profit']:
                return True, pos['take_profit'], 'Take Profit'
        else:
            if candle['high'] >= pos['stop_loss']:
                return True, pos['stop_loss'], 'Stop Loss'
            if candle['low'] <= pos['take_profit']:
                return True, pos['take_profit'], 'Take Profit'

        return False, None, None

    def close_position(self, exit_price, reason, exit_time):
        """Close position"""
        pos = self.position

        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['position_size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['position_size']

        self.balance += pnl

        trade = {
            'entry_time': str(pos['entry_time']),
            'exit_time': str(exit_time),
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'position_size': pos['position_size'],
            'setup_quality': pos['setup_quality'],
            'pnl': pnl,
            'pnl_pct': (pnl / self.balance) * 100,
            'reason': reason,
            'balance': self.balance
        }

        self.trades.append(trade)
        self.position = None

    def run_backtest(self, df_5m, df_15m, df_1h):
        """Run ultra-selective backtest"""
        print(f"\n{'='*60}")
        print(f"🔬 ULTRA-SELECTIVE BACKTEST v2.1")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Minimum Quality: {self.min_quality_stars} stars (STRICT!)")
        print(f"Volume Required: {self.volume_multiplier}x average")
        print(f"{'='*60}\n")

        current_date = None
        daily_range = None
        trades_today = 0
        skipped_setups = []

        for idx in range(3, len(df_5m)):
            candle = df_5m.iloc[idx]
            candle_date = candle['timestamp'].date()
            candle_time = candle['timestamp'].time()

            # New day
            if candle_date != current_date:
                current_date = candle_date
                daily_range = self.mark_daily_range_from_15m(df_15m, current_date)
                trades_today = 0
                self.pending_order = None

                if daily_range:
                    print(f"\n📅 {current_date} - Range: ${daily_range['high']:,.2f} / ${daily_range['low']:,.2f}")

            if not daily_range:
                continue

            # Trade window
            if not (candle_time >= datetime.strptime('09:45', '%H:%M').time() and
                    candle_time <= datetime.strptime('12:00', '%H:%M').time()):
                continue

            # Check fill
            if self.pending_order:
                if self.check_order_fill(candle):
                    stars = "⭐" * self.position['setup_quality']
                    print(f"  [{candle['timestamp'].strftime('%H:%M')}] ✅ Filled: {self.position['direction']} @ ${self.position['entry_price']:,.2f} {stars}")

            # Check exit
            if self.position:
                should_exit, exit_price, reason = self.check_exit(candle)
                if should_exit:
                    self.close_position(exit_price, reason, candle['timestamp'])
                    trades_today += 1
                    pnl_emoji = "💚" if self.trades[-1]['pnl'] > 0 else "❤️"
                    print(f"  [{candle['timestamp'].strftime('%H:%M')}] {pnl_emoji} Closed: {reason} | P&L: ${self.trades[-1]['pnl']:,.2f} | Balance: ${self.balance:,.2f}")

            # Look for setups
            if not self.position and not self.pending_order and trades_today < 1:
                if idx >= 2:
                    candle1 = df_5m.iloc[idx - 2]
                    candle2 = df_5m.iloc[idx - 1]
                    candle3 = candle

                    fvg = self.detect_fair_value_gap(
                        candle1, candle2, candle3,
                        daily_range['high'], daily_range['low']
                    )

                    if fvg:
                        current_window_5m = df_5m.iloc[max(0, idx-100):idx+1]
                        current_time = candle['timestamp']
                        df_1h_current = df_1h[df_1h['timestamp'] <= current_time]

                        trend_5m = self.get_trend_direction(current_window_5m)
                        volatility_ok = self.check_volatility(current_window_5m)
                        volume_ok = self.check_volume(candle2, current_window_5m)

                        setup_quality = self.score_setup_quality(
                            fvg, current_window_5m, df_1h_current,
                            volume_ok, volatility_ok, trend_5m
                        )

                        stars = "⭐" * setup_quality

                        # Only trade 4-5 star setups
                        if setup_quality >= self.min_quality_stars:
                            if trend_5m == fvg['type']:  # Must match trend
                                self.create_order(fvg, candle['timestamp'], setup_quality)
                                if self.pending_order:
                                    print(f"  [{candle['timestamp'].strftime('%H:%M')}] 🎯 FVG: {fvg['direction']} @ ${self.pending_order['entry_price']:,.2f} {stars} HIGH QUALITY!")
                            else:
                                skipped_setups.append({
                                    'time': candle['timestamp'],
                                    'reason': f'Trend mismatch ({trend_5m} vs {fvg["type"]})',
                                    'quality': setup_quality
                                })
                                print(f"  [{candle['timestamp'].strftime('%H:%M')}] ⏭️  Skipped: Trend mismatch {stars}")
                        else:
                            skipped_setups.append({
                                'time': candle['timestamp'],
                                'reason': f'Low quality ({setup_quality} stars, need {self.min_quality_stars}+)',
                                'quality': setup_quality
                            })
                            print(f"  [{candle['timestamp'].strftime('%H:%M')}] ⏭️  Skipped: Need {self.min_quality_stars}+ stars {stars}")

        # Close remaining
        if self.position:
            last_candle = df_5m.iloc[-1]
            self.close_position(last_candle['close'], 'Backtest End', last_candle['timestamp'])

        self.print_results(skipped_setups)

    def print_results(self, skipped_setups):
        """Print results"""
        print(f"\n{'='*60}")
        print(f"📊 ULTRA-SELECTIVE BACKTEST RESULTS v2.1")
        print(f"{'='*60}")

        if not self.trades:
            print("✅ ZERO TRADES TAKEN - This is GOOD in a bad week!")
            print(f"Preserved capital: ${self.balance:,.2f}")
            print(f"\n🛡️ Strategy correctly identified:")
            print(f"  - No {self.min_quality_stars}+ star setups")
            print(f"  - Avoided forcing trades on low-quality setups")
            print(f"  - Protected your capital!")
            print(f"\nSetups detected but skipped: {len(skipped_setups)}")
            if skipped_setups:
                print("\nSkip reasons:")
                reasons = {}
                for setup in skipped_setups:
                    reason = setup['reason']
                    reasons[reason] = reasons.get(reason, 0) + 1
                for reason, count in reasons.items():
                    print(f"  - {reason}: {count}")
            print(f"\n💡 Insight: Better to make $0 than lose money!")
            print(f"{'='*60}\n")
            return

        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        total_pnl = self.balance - self.initial_balance
        roi = (total_pnl / self.initial_balance) * 100

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance: ${self.balance:,.2f}")
        print(f"Total P&L: ${total_pnl:,.2f}")
        print(f"ROI: {roi:.2f}%")
        print(f"\n📈 Trade Statistics:")
        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"Losing Trades: {len(losing_trades)} ({100 - win_rate:.1f}%)")
        print(f"\nAverage Win: ${avg_win:,.2f}")
        print(f"Average Loss: ${avg_loss:,.2f}")

        if avg_loss != 0:
            profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades))
            print(f"Profit Factor: {profit_factor:.2f}")

        # Quality breakdown
        print(f"\n⭐ Setup Quality Distribution:")
        quality_dist = {}
        for trade in self.trades:
            quality = trade['setup_quality']
            quality_dist[quality] = quality_dist.get(quality, 0) + 1

        for quality in sorted(quality_dist.keys(), reverse=True):
            count = quality_dist[quality]
            stars = "⭐" * quality
            print(f"  {stars} ({quality} stars): {count} trades")

        print(f"\n⏭️  Filtered Out:")
        print(f"Total setups skipped: {len(skipped_setups)}")
        if skipped_setups:
            skip_reasons = {}
            for setup in skipped_setups:
                reason = setup['reason']
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            for reason, count in skip_reasons.items():
                print(f"  - {reason}: {count}")

        print(f"{'='*60}\n")

        # Save
        os.makedirs('/mnt/user-data/outputs', exist_ok=True)
        results = {
            'version': '2.1',
            'summary': {
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_pnl': total_pnl,
                'roi': roi,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'skipped_setups': len(skipped_setups)
            },
            'trades': self.trades
        }

        with open('/mnt/user-data/outputs/backtest_v2_1_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print("✅ Results saved to /mnt/user-data/outputs/backtest_v2_1_results.json")


if __name__ == "__main__":
    print("="*60)
    print("🚀 Range FVG Bot v2.1 - Ultra-Selective Backtest")
    print("   Only trades 4-5 star setups!")
    print("   Better to trade 0 times than lose money!")
    print("="*60)

    backtest = RangeFVGBacktestV2_1(
        initial_balance=10000,
        risk_per_trade=0.02,
        reward_ratio=2
    )

    print("\nFetching 5-minute data...")
    df_5m = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='5m', days=7)

    print("Fetching 15-minute data...")
    df_15m = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='15m', days=7)

    print("Fetching 1-hour data...")
    df_1h = backtest.fetch_historical_data(symbol='BTC/USDT', timeframe='1h', days=7)

    if df_5m is not None and df_15m is not None and df_1h is not None:
        backtest.run_backtest(df_5m, df_15m, df_1h)
    else:
        print("❌ Failed to fetch historical data")
